"""
Longitudinal pair dataset + collator for MAIRA-2 + DDaTR.

Consumes the longitudinal pairs your existing `curate_subset.py` already
produces. We do NOT assume its exact column names; instead everything funnels
through `FIELD_MAP` below -- point each logical field at whatever key/column
your manifest uses and the rest of the pipeline is untouched.

A manifest is a JSONL file (one JSON object per line) OR a CSV. Each record is
one longitudinal study pair and must resolve (via FIELD_MAP) to:

    current_frontal_path : str   path to the CURRENT frontal CXR (jpg/png)
    findings             : str   target Findings text (the label)
    prior_frontal_path   : str   path to the PRIOR  frontal CXR  (optional)
    prior_report         : str   prior report text                (optional)
    indication           : str   clinical context (optional, MAIRA-2 field)
    technique            : str   clinical context (optional)
    comparison           : str   clinical context (optional)
    study_id             : str   id used in the output JSON (optional but rec.)
    change_label         : str   "change"/"no_change" if you precomputed it
                                  (optional; only used to stratify at score time)

`prior_report` may instead be given as `prior_report_path` (a .txt file); set
that in FIELD_MAP and the loader reads it. Missing prior (first study) ->
leave prior_frontal_path / prior_report empty; has_prior becomes 0 and the
DDaTR modules no-op (vanilla MAIRA-2 for that case).

The collator is built for **batch_size = 1** (+ gradient accumulation), which
is what the training recipe uses and which sidesteps all multi-image padding
pain. It produces exactly the sample dict that `maira2_ddatr_model._build_inputs_embeds`
consumes.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from typing import Optional

import torch
from torch.utils.data import Dataset


# --------------------------------------------------------------------------- #
#  EDIT HERE: map logical fields -> your manifest's actual keys/columns
# --------------------------------------------------------------------------- #
FIELD_MAP = {
    "current_frontal_path": "current_image",
    "findings":             "reference_findings",   # the training target
    "prior_frontal_path":   "prior_image",
    "prior_report":         "prior_findings",
    "prior_report_path":    None,
    "indication":           "indication",
    "technique":            None,                    # this manifest has no technique field
    "comparison":           "comparison",
    "study_id":             "current_study_id",
    "change_label":         "change",
}

# MAIRA-2 stacks images in this fixed order when present. Used ONLY to split the
# processor's pixel_values stack back into named per-image tensors. Confirm with
# probe_processor.py; lateral is included for completeness even though the
# default frontal-only setup never produces it.
MAIRA2_IMAGE_STACK_ORDER = ("current_frontal", "current_lateral", "prior_frontal")


def _get(record: dict, logical: str):
    key = FIELD_MAP.get(logical)
    if key is None:
        return None
    val = record.get(key)
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return None
    return val


def _load_manifest(path: str) -> list[dict]:
    if path.endswith(".jsonl"):
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]
    if path.endswith(".json"):
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data["records"]
    if path.endswith(".csv") or path.endswith(".tsv"):
        delim = "\t" if path.endswith(".tsv") else ","
        with open(path, newline="") as f:
            return list(csv.DictReader(f, delimiter=delim))
    raise ValueError(f"unsupported manifest extension: {path}")


# --------------------------------------------------------------------------- #
#  Dataset
# --------------------------------------------------------------------------- #
class LongitudinalPairDataset(Dataset):
    """Yields per-pair dicts of raw images (PIL) + text. No tensorisation here;
    the collator owns the processor and does all tokenisation/pixel work."""

    def __init__(self, manifest_path: str, image_root: str = "",
                 require_prior: bool = False, require_findings: bool = True):
        self.records = _load_manifest(manifest_path)
        self.image_root = image_root
        if require_prior:
            self.records = [r for r in self.records if _get(r, "prior_frontal_path")]
        if require_findings:
            self.records = [r for r in self.records if _get(r, "findings")]
        if not self.records:
            raise RuntimeError(f"no usable records in {manifest_path} "
                               f"(check FIELD_MAP / filters)")

    def __len__(self):
        return len(self.records)

    def _abs(self, p: Optional[str]) -> Optional[str]:
        if p is None:
            return None
        return p if os.path.isabs(p) or not self.image_root else os.path.join(self.image_root, p)

    def _read_prior_report(self, record: dict) -> Optional[str]:
        txt = _get(record, "prior_report")
        if txt is not None:
            return txt
        rp = _get(record, "prior_report_path")
        if rp is not None:
            with open(self._abs(rp)) as f:
                return f.read().strip()
        return None

    def __getitem__(self, idx: int) -> dict:
        from PIL import Image
        r = self.records[idx]

        cur_path = self._abs(_get(r, "current_frontal_path"))
        if cur_path is None:
            raise KeyError(f"record {idx} has no current_frontal_path")
        current_frontal = Image.open(cur_path).convert("RGB")

        prior_path = self._abs(_get(r, "prior_frontal_path"))
        prior_frontal = Image.open(prior_path).convert("RGB") if prior_path else None
        prior_report = self._read_prior_report(r)
        has_prior = prior_frontal is not None  # gate on the IMAGE; DFAM needs it

        return {
            "study_id": _get(r, "study_id") or str(idx),
            "current_frontal": current_frontal,
            "prior_frontal": prior_frontal,
            "prior_report": prior_report if has_prior else None,
            "findings": _get(r, "findings"),
            "indication": _get(r, "indication"),
            "technique": _get(r, "technique"),
            "comparison": _get(r, "comparison"),
            "change_label": _get(r, "change_label"),
            "has_prior": has_prior,
        }


# --------------------------------------------------------------------------- #
#  Collator (batch_size = 1)
# --------------------------------------------------------------------------- #
@dataclass
class DDaTRCollator:
    """Turns ONE dataset item into the model's sample dict.

    processor       : the MAIRA-2 AutoProcessor (has format_and_preprocess_reporting_input)
    text_tokenizer  : the PriorTextEncoder's BERT tokenizer (for DFAM text)
    is_train        : if True, append target Findings + eos and build masked labels
    max_text_len    : truncation for the prior-report BERT tokens
    max_target_len  : truncation for the target Findings tokens
    """
    processor: object
    text_tokenizer: object
    is_train: bool = True
    max_text_len: int = 128
    max_target_len: int = 256
    image_stack_order: tuple = MAIRA2_IMAGE_STACK_ORDER
    pixel_dtype: Optional[torch.dtype] = None   # set to bf16 to match the vision tower

    def _build_prompt(self, item: dict):
        """Call MAIRA-2's processor in reporting mode -> inference prompt + pixels.

        Returns (input_ids[1,T], attention_mask[1,T], pixel_values[N,C,H,W],
                 present_blocks[list[str]]).
        """
        present = ["current_frontal"]
        lateral = item.get("current_lateral")           # None in the frontal-only setup
        if lateral is not None:
            present.append("current_lateral")

        # image_and_report mode iff we have BOTH a prior frontal and prior report;
        # providing prior_frontal is what stops the processor dropping prior_report.
        prior_frontal = item["prior_frontal"] if item["has_prior"] else None
        prior_report = item.get("prior_report") if item["has_prior"] else None
        if prior_frontal is not None:
            present.append("prior_frontal")

        # NB: the real Maira2Processor requires current_frontal / current_lateral /
        # prior_frontal / prior_report to be passed EXPLICITLY (even as None).
        proc = self.processor.format_and_preprocess_reporting_input(
            current_frontal=item["current_frontal"],
            current_lateral=lateral,
            prior_frontal=prior_frontal,
            indication=item.get("indication"),
            technique=item.get("technique"),
            comparison=item.get("comparison"),
            prior_report=prior_report,
            return_tensors="pt",
            get_grounding=False,
        )
        input_ids = proc["input_ids"]
        attention_mask = proc.get("attention_mask", torch.ones_like(input_ids))
        pixel_values = proc["pixel_values"]
        return input_ids, attention_mask, pixel_values, present

    def _split_pixels(self, pixel_values: torch.Tensor, present_blocks: list[str]):
        """Map the (N,C,H,W) stack to named per-image tensors, each (1,C,H,W).

        We trust `present_blocks` (what we actually fed the processor) and order
        them by image_stack_order. N must equal len(present_blocks).
        """
        ordered = [b for b in self.image_stack_order if b in present_blocks]
        if pixel_values.shape[0] != len(ordered):
            raise RuntimeError(
                f"processor returned {pixel_values.shape[0]} images but expected "
                f"{len(ordered)} ({ordered}); fix image_stack_order / probe_processor.py")
        named = {name: pixel_values[i:i + 1] for i, name in enumerate(ordered)}
        if self.pixel_dtype is not None:
            named = {k: v.to(self.pixel_dtype) for k, v in named.items()}
        return named

    def __call__(self, batch: list[dict]) -> dict:
        assert len(batch) == 1, "DDaTRCollator is batch_size=1 (use grad accumulation)"
        item = batch[0]

        input_ids, attention_mask, pixel_values, present = self._build_prompt(item)
        named_px = self._split_pixels(pixel_values, present)

        sample = {
            "study_id": item["study_id"],
            "change_label": item.get("change_label"),
            "has_prior": torch.tensor([1.0 if item["has_prior"] else 0.0]),
            "current_frontal_pixels": named_px["current_frontal"],
            "prior_frontal_pixels": named_px.get("prior_frontal"),  # None if absent
            "extra_blocks": ({"current_lateral": named_px["current_lateral"]}
                             if "current_lateral" in named_px else {}),
        }

        # prior report -> BERT tokens for DFAM
        if item["has_prior"] and item.get("prior_report"):
            t = self.text_tokenizer(item["prior_report"], truncation=True,
                                    max_length=self.max_text_len, return_tensors="pt")
            sample["prior_report_ids"] = t["input_ids"]
            sample["prior_report_mask"] = t["attention_mask"]
        else:
            sample["prior_report_ids"] = None
            sample["prior_report_mask"] = None

        if self.is_train:
            input_ids, attention_mask, labels = self._append_target(
                input_ids, attention_mask, item["findings"])
            sample["labels"] = labels
        sample["input_ids"] = input_ids
        sample["attention_mask"] = attention_mask
        return sample

    def _append_target(self, prompt_ids, prompt_mask, findings: str):
        """Concatenate target Findings + eos; mask the prompt out of the labels."""
        tok = self.processor.tokenizer
        eos = tok.eos_token_id
        tgt = tok(findings, add_special_tokens=False, truncation=True,
                  max_length=self.max_target_len, return_tensors="pt")["input_ids"]
        eos_col = torch.tensor([[eos]], dtype=tgt.dtype)
        tgt = torch.cat([tgt, eos_col], dim=1)               # (1, Lt+1)

        input_ids = torch.cat([prompt_ids, tgt], dim=1)
        attention_mask = torch.cat([prompt_mask, torch.ones_like(tgt)], dim=1)

        labels = torch.cat(
            [torch.full_like(prompt_ids, -100), tgt.clone()], dim=1)   # CE on Findings only
        return input_ids, attention_mask, labels


# --------------------------------------------------------------------------- #
#  CPU self-test: label masking + pixel split, using fakes (no MAIRA-2 needed)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import types

    IMG_TOKEN, TOK_PER_IMG = 999, 4

    class _FakeTok:
        eos_token_id = 2
        pad_token_id = 0
        def __call__(self, text, add_special_tokens=True, truncation=True,
                     max_length=256, return_tensors="pt"):
            # 1 id per whitespace word, offset to avoid collision with IMG_TOKEN
            ids = [10 + (len(w) % 5) for w in text.split()][:max_length]
            return {"input_ids": torch.tensor([ids]),
                    "attention_mask": torch.ones(1, len(ids), dtype=torch.long)}

    class _FakeProcessor:
        tokenizer = _FakeTok()
        def format_and_preprocess_reporting_input(self, *, frontal, prior_frontal=None,
                                                  prior_report=None, indication=None,
                                                  technique=None, comparison=None,
                                                  return_tensors="pt", get_grounding=False):
            n_imgs = 1 + (1 if prior_frontal is not None else 0)
            # prompt: [BOS, IMGxK (current), (IMGxK prior), text...]
            ids = [1]
            ids += [IMG_TOKEN] * TOK_PER_IMG
            if prior_frontal is not None:
                ids += [IMG_TOKEN] * TOK_PER_IMG
            ids += [50, 51]                       # a little instruction text
            input_ids = torch.tensor([ids])
            pixel_values = torch.randn(n_imgs, 3, 8, 8)
            return {"input_ids": input_ids,
                    "attention_mask": torch.ones_like(input_ids),
                    "pixel_values": pixel_values}

    def _fake_text_tok(text, truncation=True, max_length=128, return_tensors="pt"):
        ids = [3] + [7] * min(len(text.split()), max_length - 1)
        return {"input_ids": torch.tensor([ids]),
                "attention_mask": torch.ones(1, len(ids), dtype=torch.long)}

    proc = _FakeProcessor()
    coll = DDaTRCollator(processor=proc, text_tokenizer=_fake_text_tok, is_train=True)

    from PIL import Image
    cur = Image.new("RGB", (8, 8))
    prior = Image.new("RGB", (8, 8))

    # --- WITH prior ---
    item = {"study_id": "s1", "current_frontal": cur, "prior_frontal": prior,
            "prior_report": "old effusion stable", "findings": "small new effusion",
            "indication": None, "technique": None, "comparison": None,
            "change_label": "change", "has_prior": True}
    s = coll([item])
    n_prompt = 1 + 2 * TOK_PER_IMG + 2
    n_tgt = len("small new effusion".split()) + 1                 # + eos
    assert s["input_ids"].shape[1] == n_prompt + n_tgt
    assert (s["labels"][0, :n_prompt] == -100).all(), "prompt must be masked"
    assert (s["labels"][0, n_prompt:] != -100).all(), "target must be supervised"
    assert s["labels"][0, -1] == _FakeTok.eos_token_id, "eos supervised"
    assert s["current_frontal_pixels"].shape[0] == 1
    assert s["prior_frontal_pixels"].shape[0] == 1
    assert s["prior_report_ids"] is not None
    assert float(s["has_prior"]) == 1.0
    print("[ok] with-prior: label masking, pixel split, prior tokens correct")

    # --- WITHOUT prior ---
    item2 = dict(item, prior_frontal=None, prior_report=None, has_prior=False,
                 study_id="s2", change_label="no_change")
    s2 = coll([item2])
    n_prompt2 = 1 + TOK_PER_IMG + 2
    assert s2["input_ids"].shape[1] == n_prompt2 + n_tgt
    assert s2["prior_frontal_pixels"] is None
    assert s2["prior_report_ids"] is None
    assert float(s2["has_prior"]) == 0.0
    assert "prior_frontal" not in s2["extra_blocks"]
    print("[ok] no-prior: prior tensors absent, has_prior=0, prompt shorter")

    # --- inference mode: no labels ---
    coll_inf = DDaTRCollator(processor=proc, text_tokenizer=_fake_text_tok, is_train=False)
    s3 = coll_inf([item])
    assert "labels" not in s3
    assert s3["input_ids"].shape[1] == n_prompt           # prompt only, no target
    print("[ok] inference mode: no target appended, no labels")
    print("all data.py self-tests passed")
