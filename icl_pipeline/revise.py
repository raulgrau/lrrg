"""
Revision step: Qwen2.5-7B-Instruct rewrites only the comparison/temporal
sentences in a MAIRA-2 draft, guided by retrieved anonymized exemplars, then
the result is spliced back into the draft so non-comparison sentences are
left byte-identical.

If revision fails to parse cleanly (wrong sentence count, empty response),
`revise()` returns (original_draft, False) -- the caller (run_icl_pipeline.py)
should treat that the same as a guardrail rejection: fall back to the draft.
"""
import json
import re
from typing import List, Optional, Tuple

import torch

from config import REVISE
from retrieve import RetrievedExemplar
from temporal_utils import classify_report

_ANONYMIZE_PATTERNS = [
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"), "___"),          # dates
    (re.compile(r"\b(MRN|Accession)\s*[:#]?\s*\w+\b", re.IGNORECASE), "___"),  # ids
    (re.compile(r"\bDr\.?\s+[A-Z][a-z]+\b"), "Dr. ___"),                 # names
    (re.compile(r"\b\d{4,}\b"), "___"),                                  # any long bare numbers (study/accession-like)
]

_SYSTEM_PROMPT = (
    "You are assisting with radiology report drafting. You will be given "
    "sentences from a chest X-ray Findings section that describe change "
    "relative to a prior study, plus example sentences from other reports "
    "showing typical comparison phrasing. Rewrite the given sentences to use "
    "clear, standard radiology comparison phrasing consistent with the "
    "examples. Do not introduce new clinical findings, do not remove "
    "findings that are present, and do not change the clinical meaning. "
    "Return exactly the same number of sentences, in the same order, as a "
    "JSON list of strings and nothing else."
)


def anonymize(sentence: str) -> str:
    out = sentence
    for pattern, repl in _ANONYMIZE_PATTERNS:
        out = pattern.sub(repl, out)
    return out


class Reviser:
    def __init__(self, model_id: str, device: str = "cuda", dtype=torch.bfloat16):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = (
            AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype).to(device).eval()
        )

    def _build_messages(self, comparison_sentences: List[str], exemplars: List[RetrievedExemplar]) -> list:
        exemplar_block = "\n".join(f"- {anonymize(e.sentence)}" for e in exemplars) if exemplars else "(none available)"
        sentences_block = json.dumps(comparison_sentences)
        user_content = (
            f"Example comparison sentences from other reports:\n{exemplar_block}\n\n"
            f"Sentences to rewrite (JSON list, {len(comparison_sentences)} items):\n{sentences_block}"
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @torch.no_grad()
    def _generate(self, messages: list) -> str:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=REVISE.max_new_tokens,
            do_sample=REVISE.temperature > 0,
            temperature=max(REVISE.temperature, 1e-5),
        )
        gen_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
        return self.tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

    @staticmethod
    def _parse_revised_sentences(raw_output: str, expected_count: int) -> Optional[List[str]]:
        # Try direct JSON parse first; fall back to extracting the first
        # `[...]` block in case the model wraps it in prose despite instructions.
        candidates = [raw_output]
        bracket_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
        if bracket_match:
            candidates.append(bracket_match.group(0))

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list) and len(parsed) == expected_count and all(
                isinstance(s, str) for s in parsed
            ):
                return parsed
        return None

    def revise(self, draft_text: str, exemplars: List[RetrievedExemplar]) -> Tuple[str, bool]:
        """
        Returns (result_text, success). On failure, result_text == draft_text
        unchanged and success is False -- caller should treat this as an
        automatic guardrail reject (no point re-scoring an unchanged report).
        """
        sentences, flags = classify_report(draft_text)
        if not sentences:
            return draft_text, False

        comparison_indices = [i for i, f in enumerate(flags) if f == 1]
        if not comparison_indices:
            # nothing to revise -- draft passes through unchanged, which is
            # a legitimate (not a failure) outcome.
            return draft_text, True

        comparison_sentences = [sentences[i] for i in comparison_indices]
        messages = self._build_messages(comparison_sentences, exemplars)
        raw_output = self._generate(messages)
        revised = self._parse_revised_sentences(raw_output, expected_count=len(comparison_sentences))
        if revised is None:
            return draft_text, False

        spliced = list(sentences)
        for idx, new_sentence in zip(comparison_indices, revised):
            spliced[idx] = new_sentence.strip()
        return " ".join(spliced), True
