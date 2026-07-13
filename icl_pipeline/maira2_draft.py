"""
MAIRA-2 frozen-backbone drafter: produces the initial Findings section that
the rest of the ICL pipeline revises. No training, no LoRA/DDaTR -- plain
inference in `image_and_report` mode (current frontal + prior frontal +
prior report).

This mirrors run_ablation.py's `generate()` (its "with prior, image_and_report"
arm) almost exactly -- that function is already confirmed working against the
gated MAIRA-2 checkpoint on cgpool, so this class deliberately does not
deviate from its processor call, decode, and `convert_output_to_plaintext_or_grounded_sequence`
pattern. The one difference: run_ablation.py hardcodes comparison="None."
because it's isolating prior-report/image as the single manipulated variable
across a with/without-prior ablation. ICL always runs the with-prior arm and
wants realistic context, so `comparison` is passed through from the manifest
instead of being neutralized.

MAIRA-2 access: gated but instant-grant -- accept the license at
https://huggingface.co/microsoft/maira-2 while logged in, then
`huggingface-cli login` / `hf auth login` on the pool machine.
"""
from typing import Optional

import torch
from PIL import Image


class MAIRA2Drafter:
    def __init__(self, model_id: str, device: str = "cuda", dtype=torch.bfloat16):
        from transformers import AutoModelForCausalLM, AutoProcessor

        self.device = device
        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        self.model = (
            AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True, torch_dtype=dtype)
            .to(device)
            .eval()
        )

    @staticmethod
    def _load_image(path: str) -> Image.Image:
        # MIMIC JPGs are single-channel; RAD-DINO expects 3 channels.
        return Image.open(path).convert("RGB")

    @torch.no_grad()
    def draft(
        self,
        current_frontal_path: str,
        prior_frontal_path: Optional[str],
        prior_report_text: Optional[str],
        indication: Optional[str] = None,
        comparison: Optional[str] = None,
        max_new_tokens: int = 300,
    ) -> str:
        """
        Returns the decoded Findings-section draft text for one case.

        Note (per project memory / data.py's FIELD_MAP comment): the
        processor silently drops prior_report_text if prior_frontal_path is
        None. Cases missing either the prior image or prior report should be
        filtered out upstream (run_icl_pipeline.py already restricts to the
        valid prior-conditioned population) rather than passed here with only
        one of the two prior fields set, to avoid a silent mismatch between
        what you think the model saw and what it actually saw.
        """
        current_frontal = self._load_image(current_frontal_path)
        prior_frontal = self._load_image(prior_frontal_path) if prior_frontal_path else None

        inputs = self.processor.format_and_preprocess_reporting_input(
            current_frontal=current_frontal,
            current_lateral=None,
            prior_frontal=prior_frontal,
            indication=indication,
            technique=None,  # manifest has no technique field (see config.py note)
            comparison=comparison,
            prior_report=prior_report_text if prior_frontal is not None else None,
            return_tensors="pt",
            get_grounding=False,
        ).to(self.device)

        output_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens, use_cache=True)
        prompt_length = inputs["input_ids"].shape[-1]
        decoded = self.processor.decode(output_ids[0][prompt_length:], skip_special_tokens=True).lstrip()
        return self.processor.convert_output_to_plaintext_or_grounded_sequence(decoded)
