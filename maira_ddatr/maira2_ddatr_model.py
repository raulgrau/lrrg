"""
MAIRA-2 + DDaTR integration.

Strategy: instead of patching MAIRA-2's internal `get_image_features` (whose
signature drifts across transformers versions), we *take over the LLaVA
multimodal merge ourselves*:

    1. text  -> inputs_embeds = embed_tokens(input_ids)
    2. images-> DDaTR-enhanced features for the CURRENT FRONTAL (via InjectedRadDino),
               vanilla features for any other image block (via the base vision tower),
               each passed through MAIRA-2's own multi_modal_projector
    3. scatter the per-image features into inputs_embeds at <image> positions
       (exactly LLaVA's masked_scatter), in image-block order
    4. call model.language_model(inputs_embeds=..., labels=...) with pixel_values=None

This reproduces base MAIRA-2 exactly when DDaTR is disabled, and changes ONLY how
the current frontal's visual tokens are computed when it is enabled. The prior
*report text* stays in the prompt either way (image_and_report mode does not drop
it; the drop bug only triggers when prior_frontal is None).

Two prior-image modes:
    keep_as_tokens       : prior frontal also occupies LLM token slots (vanilla),
                           and DDaTR additionally makes the current frontal
                           difference-aware. Robust; no token surgery. DEFAULT.
    strip_to_encoder_only: prior frontal does NOT occupy LLM token slots; it feeds
                           only the DDaTR encoder fusion. Isolates encoder-fusion vs
                           late-fusion (the paper's clean hypothesis test), but
                           requires the verified IMAGE_BLOCK_ORDER below.

>>> EVERYTHING YOU MUST CONFIRM ON THE CLUSTER LIVES IN `MAIRA2Spec` BELOW. <<<
Run `python probe_processor.py` once; it prints every value needed to fill it in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import root
from typing import Optional

import torch
import torch.nn as nn

from raddino_injection import InjectedRadDino, resolve_injection_indices


# =========================================================================== #
#  CLUSTER-VERIFY SPEC  (confirm once with probe_processor.py)
# =========================================================================== #
@dataclass
class MAIRA2Spec:
    model_id: str = "microsoft/maira-2"

    # -- attribute paths on the loaded MAIRA-2 model -----------------------
    # confirmed via probe_processor.py on the cluster (2026-07-12)
    vision_tower_attr: str = "vision_tower"
    projector_attr: str = "multi_modal_projector"
    language_model_attr: str = "language_model"

    # -- vision tower internals (standard HF Dinov2; usually correct) ------
    vt_embeddings_attr: str = "embeddings"
    vt_layers_path: tuple[str, str] = ("encoder", "layer")
    vt_layernorm_attr: str = "layernorm"
    # confirmed via probe_processor.py on the cluster (2026-07-13): real
    # vision-tower forward reports last_hidden tokens=1370 -> grid 37x37,
    # num_prefix_tokens=1, hidden_dim=768. (config.image_seq_length=576 is a
    # separate LLaVA-side field, unrelated to the raw ViT token grid -- ignore it.)
    num_prefix_tokens: int = 1                     # CLS only -> 1+37*37 = 1370
    grid_hw: tuple[int, int] = (37, 37)
    hidden_dim: int = 768

    # -- LLaVA feature selection (read from model.config) ------------------
    # confirmed via probe_processor.py on the cluster (2026-07-12)
    image_token_index: int = 32204
    vision_feature_layer: int = -1
    vision_feature_select_strategy: str = "default"  # drops CLS/prefix tokens

    # -- processor image-block layout (only needed for strip mode) ---------
    # order of image blocks as they appear in the prompt token sequence.
    # confirmed via probe_processor.py (2026-07-13): 2 image spans of 1369
    # tokens each, current-frontal span starts before prior-frontal span in
    # the real prompt -- matches this order. (pixel_values stack order is
    # assumed to match token order; not independently verified pixel-by-pixel.)
    image_block_order: tuple[str, ...] = ("current_frontal", "prior_frontal")

    # -- modules to keep in bf16 (NOT 4-bit quantized) ---------------------
    # the vision tower and projector are trained/injected, so never quantize them
    quant_skip_modules: tuple[str, ...] = ("vision_tower", "multi_modal_projector")

    def normalized_feature_layer(self, num_layers: int) -> int:
        return self.vision_feature_layer % (num_layers + 1)  # hidden_states has L+1 entries


SPEC = MAIRA2Spec()


# =========================================================================== #
#  Prior-report text encoder (frozen) + trainable projection
# =========================================================================== #
class PriorTextEncoder(nn.Module):
    """Encode the prior report into token features for DFAM.

    Defaults to bert-base-uncased to mirror the DDaTR repo exactly (hidden 768).
    Swap to 'microsoft/BiomedVLP-CXR-BERT-specialized' for the clinical variant
    (also hidden 768; pass trust_remote_code=True).
    """

    def __init__(self, model_name: str = "bert-base-uncased",
                 out_dim: int = 768, trust_remote_code: bool = False) -> None:
        super().__init__()
        from transformers import AutoModel, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=trust_remote_code)
        self.encoder = AutoModel.from_pretrained(model_name, trust_remote_code=trust_remote_code)
        self.encoder.eval()
        for p in self.encoder.parameters():
            p.requires_grad = False
        in_dim = self.encoder.config.hidden_size
        # identity-initialised trainable projection (no-op at start if dims match)
        self.proj = nn.Linear(in_dim, out_dim)
        if in_dim == out_dim:
            with torch.no_grad():
                self.proj.weight.copy_(torch.eye(out_dim))
                self.proj.bias.zero_()

    @torch.no_grad()
    def _encode_frozen(self, input_ids, attention_mask):
        return self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state

    def forward(self, input_ids, attention_mask):
        feats = self._encode_frozen(input_ids, attention_mask)   # (B, L, in_dim) frozen
        return self.proj(feats), attention_mask                  # (B, L, out_dim), (B, L)

    def tokenize(self, text: str, max_len: int = 128):
        return self.tokenizer(text, truncation=True, max_length=max_len, return_tensors="pt")


# =========================================================================== #
#  LLaVA-style multimodal merge (taken over here)
# =========================================================================== #
def select_and_project(last_hidden, hidden_states, projector, spec: MAIRA2Spec, num_layers: int):
    """Pick the configured vision feature layer, apply CLS strategy, project."""
    feat = hidden_states[spec.normalized_feature_layer(num_layers)]
    if spec.vision_feature_select_strategy == "default":
        feat = feat[:, spec.num_prefix_tokens:]          # drop CLS/prefix
    elif spec.vision_feature_select_strategy != "full":
        raise ValueError(spec.vision_feature_select_strategy)
    return projector(feat)                                # (B, tokens, llm_dim)


def scatter_image_features(inputs_embeds, input_ids, image_features_in_block_order, image_token_index):
    """LLaVA masked_scatter: drop per-image features into <image> slots, in order.

    image_features_in_block_order: list of (n_img_i, tokens_i, llm_dim) tensors,
    concatenated row-major to match the order image blocks appear in input_ids.
    """
    special_mask = (input_ids == image_token_index).unsqueeze(-1)        # (B, T, 1)
    flat = torch.cat([f.reshape(-1, f.shape[-1]) for f in image_features_in_block_order], dim=0)
    n_slots = int(special_mask.sum().item())
    assert flat.shape[0] == n_slots, (
        f"image feature tokens ({flat.shape[0]}) != <image> placeholder slots "
        f"({n_slots}); check tokens-per-image and image_block_order"
    )
    flat = flat.to(inputs_embeds.dtype)
    return inputs_embeds.masked_scatter(special_mask, flat)


class DDaTRVisionMerger(nn.Module):
    """Produces DDaTR-enhanced current-frontal features + vanilla features for
    every other image block, projected into the LLM token space."""

    def __init__(self, base_vision_tower, injected: InjectedRadDino, projector,
                 spec: MAIRA2Spec) -> None:
        super().__init__()
        self.base_vt = base_vision_tower          # frozen, for vanilla image blocks
        self.injected = injected                  # DDaTR-wrapped, for current frontal
        self.projector = projector
        self.spec = spec
        self.num_layers = injected.num_layers

    @torch.no_grad()
    def _vanilla_hidden(self, pixels):
        # Route through the injected module with has_prior=0 -> an exact vanilla
        # RAD-DINO forward (DDaTR residuals gated off). This (a) avoids MAIRA-2's
        # vision tower being a Backbone, whose output is a BackboneOutput with no
        # .last_hidden_state, and (b) guarantees prior/lateral image blocks get
        # IDENTICAL hidden-state construction to the current frontal, so their
        # projected features can't land on a different scale. None-safe: with
        # has_prior=0 the injected forward never dereferences prior_pixels/txt.
        #
        # @torch.no_grad(): has_prior=0 means the DDaTR residual is provably zero
        # (see raddino_injection.py's self-test), so this path only ever feeds the
        # trainable projector as a VALUE -- no gradient needs to reach back through
        # it. Without this, every call still ran the full DFAM/DDAM forward (conv
        # branches, attention, gating) just to multiply the result by zero and
        # build a backward graph nothing uses. Called at least once per training
        # step (prior_frontal in keep_as_tokens mode), more with extra_vanilla_blocks.
        B = pixels.shape[0]
        zeros = torch.zeros(B, device=pixels.device, dtype=pixels.dtype)
        return self.injected(pixels, None, None, None, zeros)

    def forward(self, *, cur_frontal, prior_frontal, txt, txt_mask, has_prior,
                extra_vanilla_blocks: Optional[dict[str, torch.Tensor]] = None):
        """Returns a dict block_name -> projected features (1, tokens, llm_dim)."""
        feats: dict[str, torch.Tensor] = {}

        # current frontal: DDaTR-enhanced
        last, hs = self.injected(cur_frontal, prior_frontal, txt, txt_mask, has_prior)
        feats["current_frontal"] = select_and_project(last, hs, self.projector, self.spec, self.num_layers)

        # prior frontal as vanilla LLM tokens (only used in keep_as_tokens mode)
        if prior_frontal is not None:
            last_p, hs_p = self._vanilla_hidden(prior_frontal)
            feats["prior_frontal"] = select_and_project(last_p, hs_p, self.projector, self.spec, self.num_layers)

        # any other current image blocks (e.g. lateral)
        for name, pix in (extra_vanilla_blocks or {}).items():
            last_e, hs_e = self._vanilla_hidden(pix)
            feats[name] = select_and_project(last_e, hs_e, self.projector, self.spec, self.num_layers)
        return feats


# =========================================================================== #
#  Model assembly: load MAIRA-2 (4-bit), wrap vision tower, attach QLoRA
# =========================================================================== #
@dataclass
class DDaTRBundle:
    model: nn.Module                 # MAIRA-2 (LLM 4-bit + LoRA, projector trainable)
    processor: object
    merger: DDaTRVisionMerger
    text_encoder: PriorTextEncoder
    spec: MAIRA2Spec
    injected: InjectedRadDino
    prior_image_mode: str
    extra_trainable: nn.ModuleList = field(default_factory=nn.ModuleList)


def build_model(
    *,
    injection: str | list[int] = "M1",
    prior_image_mode: str = "keep_as_tokens",
    text_encoder_name: str = "bert-base-uncased",
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    train_projector_full: bool = True,
    norm: str = "group",
    num_heads: int = 12,
    load_in_4bit: bool = True,
    device: str = "cuda",
    spec: MAIRA2Spec = SPEC,
    use_gradient_checkpointing: bool = True,
    grad_checkpointing_reentrant: bool = False,
) -> DDaTRBundle:
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    assert prior_image_mode in ("keep_as_tokens", "strip_to_encoder_only")

    quant = None
    if load_in_4bit:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            # keep vision tower + projector OUT of 4-bit (we train/inject them)
            llm_int8_skip_modules=list(spec.quant_skip_modules),
        )

    # sdpa attention is meaningfully faster than eager for the 7B Vicuna decoder,
    # especially combined with gradient checkpointing. Not all trust_remote_code
    # models wire this kwarg through cleanly -- fall back to eager (the previous
    # default) if MAIRA-2's custom modeling code rejects it, rather than hard
    # failing model load.
    _from_pretrained_kwargs = dict(
        trust_remote_code=True,
        quantization_config=quant,
        torch_dtype=torch.bfloat16,
        device_map={"": device} if load_in_4bit else None,
    )
    try:
        model = AutoModelForCausalLM.from_pretrained(
            spec.model_id, attn_implementation="sdpa", **_from_pretrained_kwargs)
    except (TypeError, ValueError) as e:
        print(f"[build_model] attn_implementation='sdpa' rejected ({e}); "
              f"falling back to eager attention.")
        model = AutoModelForCausalLM.from_pretrained(spec.model_id, **_from_pretrained_kwargs)

    # discover submodules
    def _resolve(root, dotted):
        """getattr that walks 'a.b.c'."""
        obj = root
        for part in dotted.split("."):
            obj = getattr(obj, part)
        return obj

    vision_tower = _resolve(model, spec.vision_tower_attr)        # e.g. "model.vision_tower"
    projector    = _resolve(model, spec.projector_attr)
    language_model = _resolve(model, spec.language_model_attr)

    # build the DDaTR-injected vision encoder over the SAME (frozen) RAD-DINO
    injected = InjectedRadDino(
        vision_tower,
        injection=injection,
        embeddings_attr=spec.vt_embeddings_attr,
        layers_path=spec.vt_layers_path,
        layernorm_attr=spec.vt_layernorm_attr,
        num_prefix_tokens=spec.num_prefix_tokens,
        grid_hw=spec.grid_hw,
        hidden_dim=spec.hidden_dim,
        txt_dim=spec.hidden_dim,
        num_heads=num_heads,
        norm=norm,
    ).to(device=device, dtype=torch.bfloat16)

    # sanity: the injected enhancement must be visible at the selected feature layer
    # (skipped for injection="none" -- the fine-tuned baseline has no injection).
    if injected.injection_indices:
        sel = spec.normalized_feature_layer(injected.num_layers)    # index into hidden_states
        max_inj = max(injected.injection_indices) + 1               # hidden_states index after that block
        assert max_inj >= sel, (
            f"deepest injection feeds hidden_states[{max_inj}] but features are read at "
            f"hidden_states[{sel}]; injection happens AFTER the read and would be ignored. "
            f"For M1, inject at the feature layer (block {sel})."
        )

    text_encoder = PriorTextEncoder(
        text_encoder_name, out_dim=spec.hidden_dim,
        trust_remote_code=("CXR-BERT" in text_encoder_name),
    ).to(device=device, dtype=torch.bfloat16)

    # ---- QLoRA: 4-bit base + LoRA on Vicuna q/v ----
    if load_in_4bit:
        # Profiling on cgpool (2026-07): backward is 66% of step time vs 27%
        # forward -- a ~2.5x bwd/fwd ratio, higher than the ~2x you'd expect
        # without checkpointing. That gap is checkpoint recomputation (part of
        # the forward re-runs during backward to avoid storing activations).
        # use_reentrant=False (PyTorch's newer checkpoint impl) is usually
        # cheaper than the legacy reentrant default HF/peft still falls back
        # to if you don't ask -- try this first. If VRAM allows, try
        # use_gradient_checkpointing=False entirely (biggest win, but may OOM
        # at batch=1 on a 24GB 3090; more likely to fit on bigger compute).
        ckpt_kwargs = dict(use_gradient_checkpointing=use_gradient_checkpointing)
        if use_gradient_checkpointing:
            ckpt_kwargs["gradient_checkpointing_kwargs"] = {
                "use_reentrant": grad_checkpointing_reentrant}
        try:
            model = prepare_model_for_kbit_training(model, **ckpt_kwargs)
        except TypeError:
            # older peft: no gradient_checkpointing_kwargs passthrough
            model = prepare_model_for_kbit_training(
                model, use_gradient_checkpointing=use_gradient_checkpointing)
        # prepare_model_for_kbit_training walks ALL of model.parameters() and
        # upcasts any bf16/fp16 param back to fp32 (standard peft behavior for
        # training stability). vision_tower is a SHARED object between `model`
        # and injected.embeddings/injected.layers/injected.layernorm, so this
        # silently reverts the bf16 cast at line ~292. injected.blocks (DFAM/DDAM)
        # live outside model's parameter tree and are untouched, so they stay
        # bf16 -- causing "Input type float and bias type BFloat16" the moment
        # fp32 patches hit a bf16 DDaTR block. Re-cast the vision tower now.
        injected.to(dtype=torch.bfloat16)
    lora_cfg = LoraConfig(
        r=lora_r, lora_alpha=lora_alpha, lora_dropout=lora_dropout,
        target_modules=["q_proj", "v_proj"], bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)

    # re-fetch submodules through the PEFT wrapper (names get a base_model. prefix)
    def _find(mod, attr):
        for name, m in mod.named_modules():
            if name.endswith(attr):
                return m
        raise AttributeError(attr)

    projector = _find(model, spec.projector_attr)
    # same reason as the injected.to() call above: prepare_model_for_kbit_training
    # already reverted this module to fp32 before we re-fetched it here.
    projector.to(dtype=torch.bfloat16)

    # mark our trainable params: DDaTR blocks, text projection, (optionally) projector
    for p in injected.blocks.parameters():
        p.requires_grad = True
    for p in text_encoder.proj.parameters():
        p.requires_grad = True
    if train_projector_full:
        for p in projector.parameters():
            p.requires_grad = True

    merger = DDaTRVisionMerger(vision_tower, injected, projector, spec).to(device)

    extra = nn.ModuleList([injected.blocks, text_encoder.proj])
    if train_projector_full:
        extra.append(projector)

    bundle = DDaTRBundle(model, AutoProcessor.from_pretrained(spec.model_id, trust_remote_code=True),
                         merger, text_encoder, spec, injected, prior_image_mode, extra)
    _report_trainable(bundle)
    return bundle


def _report_trainable(bundle: DDaTRBundle):
    seen = set()
    total = train = 0
    for mod in (bundle.model, bundle.injected, bundle.text_encoder):
        for p in mod.parameters():
            if id(p) in seen:
                continue
            seen.add(id(p))
            total += p.numel()
            if p.requires_grad:
                train += p.numel()
    print(f"[params] trainable {train/1e6:.1f}M / total {total/1e6:.1f}M "
          f"({100*train/max(total,1):.3f}%)")


# =========================================================================== #
#  Forward / generate
# =========================================================================== #
def _build_inputs_embeds(bundle: DDaTRBundle, sample: dict, device: str):
    """Shared logic for step() and generate(): returns (inputs_embeds, attn, labels?)."""
    model, spec = bundle.model, bundle.spec
    input_ids = sample["input_ids"].to(device)            # (1, T)
    attn = sample["attention_mask"].to(device)
    has_prior = sample["has_prior"].to(device)            # (1,)

    # prior report text -> DFAM features
    if sample.get("prior_report_ids") is not None and bool(has_prior.item()):
        txt, txt_mask = bundle.text_encoder(
            sample["prior_report_ids"].to(device), sample["prior_report_mask"].to(device))
    else:
        txt = torch.zeros(1, 1, spec.hidden_dim, device=device, dtype=torch.bfloat16)
        txt_mask = torch.zeros(1, 1, device=device)

    prior_frontal = sample.get("prior_frontal_pixels")
    prior_frontal = prior_frontal.to(device) if prior_frontal is not None else None

    feats = bundle.merger(
        cur_frontal=sample["current_frontal_pixels"].to(device),
        prior_frontal=prior_frontal,
        txt=txt, txt_mask=txt_mask, has_prior=has_prior,
        extra_vanilla_blocks={k: v.to(device) for k, v in sample.get("extra_blocks", {}).items()},
    )

    # assemble features in the prompt's image-block order
    order = list(spec.image_block_order)
    if bundle.prior_image_mode == "strip_to_encoder_only":
        order = [b for b in order if b != "prior_frontal"]   # prior not an LLM block
    feats_in_order = [feats[b] for b in order if b in feats]

    inputs_embeds = model.get_input_embeddings()(input_ids)
    inputs_embeds = scatter_image_features(
        inputs_embeds, input_ids, feats_in_order, spec.image_token_index)

    labels = sample.get("labels")
    labels = labels.to(device) if labels is not None else None
    return inputs_embeds, attn, labels


def ddatr_step(bundle: DDaTRBundle, sample: dict, device: str = "cuda"):
    """One teacher-forced forward; returns loss (Findings-only CE via masked labels)."""
    inputs_embeds, attn, labels = _build_inputs_embeds(bundle, sample, device)
    out = bundle.model(inputs_embeds=inputs_embeds, attention_mask=attn,
                       labels=labels, pixel_values=None)
    return out.loss


@torch.no_grad()
def ddatr_generate(bundle: DDaTRBundle, sample: dict, device: str = "cuda",
                   max_new_tokens: int = 256, num_beams: int = 1):
    inputs_embeds, attn, _ = _build_inputs_embeds(bundle, sample, device)
    gen = bundle.model.generate(
        inputs_embeds=inputs_embeds, attention_mask=attn,
        max_new_tokens=max_new_tokens, num_beams=num_beams,
        pad_token_id=bundle.processor.tokenizer.pad_token_id, pixel_values=None)
    return bundle.processor.tokenizer.batch_decode(gen, skip_special_tokens=True)[0].strip()


# =========================================================================== #
#  CPU self-test for the scatter/merge ORDERING math (no MAIRA-2 needed)
# =========================================================================== #
if __name__ == "__main__":
    torch.manual_seed(0)
    IMG = 999                      # fake image_token_index
    llm_dim, tok = 8, 3            # tiny: 3 tokens per image block

    # sequence: [txt, IMG x3 (block A), txt, IMG x3 (block B), txt]
    input_ids = torch.tensor([[1, IMG, IMG, IMG, 2, IMG, IMG, IMG, 3]])
    inputs_embeds = torch.zeros(1, input_ids.shape[1], llm_dim)

    feat_A = torch.full((1, tok, llm_dim), 1.0)   # block A -> all ones
    feat_B = torch.full((1, tok, llm_dim), 2.0)   # block B -> all twos

    merged = scatter_image_features(inputs_embeds.clone(), input_ids, [feat_A, feat_B], IMG)
    # positions 1,2,3 should be 1.0 ; positions 5,6,7 should be 2.0 ; rest 0
    expect = torch.zeros(1, 9, llm_dim)
    expect[0, 1:4] = 1.0
    expect[0, 5:8] = 2.0
    assert torch.allclose(merged, expect), "scatter ordering wrong"
    print("[ok] masked_scatter places image blocks in sequence order")

    # block-order respected: swapping the feature list must change the result
    merged_swapped = scatter_image_features(inputs_embeds.clone(), input_ids, [feat_B, feat_A], IMG)
    assert not torch.allclose(merged_swapped, expect)
    print("[ok] feature-list order maps to block order (strip mode must drop the right block)")

    # slot-count mismatch is caught loudly
    try:
        scatter_image_features(inputs_embeds.clone(), input_ids, [feat_A], IMG)
        raise SystemExit("should have raised")
    except AssertionError:
        print("[ok] slot/feature count mismatch raises")
