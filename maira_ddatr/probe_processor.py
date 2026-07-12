"""
Run this ONCE on the cluster (where MAIRA-2 is downloaded) to fill in every
value in `MAIRA2Spec`. It loads the real model + processor, inspects the module
tree and config, builds a real image_and_report prompt, and prints a
ready-to-paste spec plus the few things you must eyeball.

  python probe_processor.py                       # uses synthetic blank images
  python probe_processor.py --current a.jpg --prior b.jpg   # use real CXRs

No network needed in the default mode (blank PIL images exercise the exact same
prompt/token machinery). Nothing here is destructive.
"""

from __future__ import annotations

import argparse


def _runs_of(value, seq):
    """Return [(start, length), ...] contiguous runs of `value` in a 1-D list."""
    runs, i, n = [], 0, len(seq)
    while i < n:
        if seq[i] == value:
            j = i
            while j < n and seq[j] == value:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_id", default="microsoft/maira-2")
    ap.add_argument("--current", default="", help="path to a current frontal CXR")
    ap.add_argument("--prior", default="", help="path to a prior frontal CXR")
    args = ap.parse_args()

    import torch
    from PIL import Image
    from transformers import AutoModelForCausalLM, AutoProcessor

    print("=" * 72)
    print("loading model + processor (this pulls the gated MAIRA-2 weights) ...")
    model = AutoModelForCausalLM.from_pretrained(args.model_id, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(args.model_id, trust_remote_code=True)
    model.eval()

    # ---------------------------------------------------------------- module tree
    print("\n" + "=" * 72)
    print("[1] model.named_children()  ->  vision/projector/language attr names")
    children = [n for n, _ in model.named_children()]
    print("   ", children)
    vt_attr = next((c for c in children if "vision" in c.lower()), "vision_model")
    proj_attr = next((c for c in children
                      if "project" in c.lower() or "modal" in c.lower()), "multi_modal_projector")
    lm_attr = next((c for c in children
                    if "language" in c.lower() or "model" == c.lower()
                    or "llm" in c.lower()), "language_model")
    print(f"    -> vision_tower_attr   = {vt_attr!r}")
    print(f"    -> projector_attr      = {proj_attr!r}")
    print(f"    -> language_model_attr = {lm_attr!r}")

    # ---------------------------------------------------------------- vision tower
    print("\n" + "=" * 72)
    print("[2] vision tower internals")
    vt = getattr(model, vt_attr)
    vt_children = [n for n, _ in vt.named_children()]
    print("    vision tower children:", vt_children)
    emb_attr = "embeddings" if "embeddings" in vt_children else vt_children[0]
    has_encoder = any(n == "encoder" for n in vt_children)
    ln_attr = next((n for n in vt_children if "layernorm" in n.lower()
                    or n.lower() == "norm"), "layernorm")
    try:
        layers = vt.encoder.layer if has_encoder else None
        n_layers = len(layers)
        layers_path = ("encoder", "layer")
    except Exception:
        n_layers, layers_path = None, ("encoder", "layer")
    print(f"    -> vt_embeddings_attr = {emb_attr!r}")
    print(f"    -> vt_layers_path     = {layers_path}  (num layers = {n_layers})")
    print(f"    -> vt_layernorm_attr  = {ln_attr!r}")

    # patch grid + prefix tokens from a forward on a blank image
    cur_img = (Image.open(args.current).convert("RGB") if args.current
               else Image.new("RGB", (518, 518)))
    prior_img = (Image.open(args.prior).convert("RGB") if args.prior
                 else Image.new("RGB", (518, 518)))
    try:
        px = processor.image_processor(cur_img, return_tensors="pt")["pixel_values"]
        # vt(px) returns a BackboneOutput with no .last_hidden_state (confirmed on
        # cluster 2026-07-12) -- same reason maira2_ddatr_model.py's _vanilla_hidden
        # walks .embeddings / .encoder.layer / .layernorm directly instead of
        # calling the module's own forward(). Mirror that here.
        with torch.no_grad():
            hidden = vt.embeddings(px)
            all_hidden = [hidden]
            for layer in vt.encoder.layer:
                out = layer(hidden)
                hidden = out[0] if isinstance(out, tuple) else out
                all_hidden.append(hidden)
            last_hidden = vt.layernorm(hidden) if hasattr(vt, "layernorm") else hidden
        n_tokens = last_hidden.shape[1]
        # infer grid: largest square <= n_tokens, remainder = prefix tokens
        import math
        side = int(math.isqrt(n_tokens))
        while side > 0 and (n_tokens - side * side) not in (0, 1, 5):
            side -= 1
        prefix = n_tokens - side * side
        print(f"    vision last_hidden tokens = {n_tokens}  -> grid {side}x{side}, "
              f"num_prefix_tokens = {prefix}")
        print(f"    -> grid_hw = ({side}, {side})   num_prefix_tokens = {prefix}")
        print(f"    -> hidden_dim = {last_hidden.shape[-1]}")
        print(f"    vision hidden_states list length = {len(all_hidden)} "
              f"(=> hidden_states[-1] is index {len(all_hidden)-1})")
        if n_tokens - prefix != 37 * 37:
            print(f"    [warn] patch count {n_tokens - prefix} != 37*37=1369 "
                  f"(config.image_seq_length may reflect a different grid/pooling -- "
                  f"cross-check against section [3] before trusting grid_hw)")
    except Exception as e:
        print("    [warn] could not run vision tower forward:", e)

    # ---------------------------------------------------------------- config fields
    print("\n" + "=" * 72)
    print("[3] model.config  ->  LLaVA feature-selection fields")
    cfg = model.config
    for field in ("image_token_index", "image_token_id", "vision_feature_layer",
                  "vision_feature_select_strategy", "image_seq_length"):
        print(f"    config.{field} = {getattr(cfg, field, '<absent>')}")
    img_tok = getattr(cfg, "image_token_index", getattr(cfg, "image_token_id", None))

    # ---------------------------------------------------------------- prompt layout
    print("\n" + "=" * 72)
    print("[4] real image_and_report prompt -> image-block order & tokens/image")
    try:
        # signature now requires current_frontal / current_lateral explicitly
        # (confirmed on cluster 2026-07-12: TypeError missing these 2 args).
        # current_lateral is passed as None -- confirm the processor accepts
        # that for a frontal-only, prior-conditioned sample.
        proc = processor.format_and_preprocess_reporting_input(
            current_frontal=cur_img, current_lateral=None, prior_frontal=prior_img,
            indication="None.", technique="PA and lateral views.",
            comparison="None.", prior_report="Stable cardiomegaly. No effusion.",
            return_tensors="pt", get_grounding=False,
        )
        ids = proc["input_ids"][0].tolist()
        pv = proc["pixel_values"]
        print(f"    pixel_values shape = {tuple(pv.shape)}  (dim0 = #images in stack)")

        if img_tok is None:
            # infer the image token as the id forming the longest contiguous run
            from collections import Counter
            run_counter = Counter()
            for v in set(ids):
                rs = _runs_of(v, ids)
                if rs:
                    run_counter[v] = max(L for _, L in rs)
            img_tok = run_counter.most_common(1)[0][0]
            print(f"    [inferred] image_token_index = {img_tok} "
                  f"(longest repeated run); CONFIRM this matches config")
        runs = _runs_of(img_tok, ids)
        print(f"    -> image_token_index = {img_tok}")
        print(f"    #image spans = {len(runs)}  (expect 2: current, prior)")
        for k, (start, length) in enumerate(runs):
            print(f"        span {k}: start={start:4d}  tokens={length}")
        if runs:
            lengths = {L for _, L in runs}
            print(f"    tokens-per-image = {lengths} "
                  f"(should equal grid + num_prefix_tokens)")
        print("    >>> ASSUMPTION: span order is (current_frontal, prior_frontal) and")
        print("        pixel_values stacks in the SAME order. If the model card or a")
        print("        quick pixel check says otherwise, set image_block_order /")
        print("        MAIRA2_IMAGE_STACK_ORDER accordingly.")
    except AttributeError:
        print("    [warn] processor has no format_and_preprocess_reporting_input.")
        print("    available callables:",
              [m for m in dir(processor) if "report" in m.lower() or "process" in m.lower()])
    except Exception as e:
        print("    [warn] prompt build failed:", e)

    # ---------------------------------------------------------------- paste block
    print("\n" + "=" * 72)
    print("[5] PASTE-READY MAIRA2Spec (verify the few items flagged above):")
    print("-" * 72)
    print(f"""SPEC = MAIRA2Spec(
    model_id="{args.model_id}",
    vision_tower_attr="{vt_attr}",
    projector_attr="{proj_attr}",
    language_model_attr="{lm_attr}",
    vt_embeddings_attr="{emb_attr}",
    vt_layers_path={layers_path!r},
    vt_layernorm_attr="{ln_attr}",
    image_token_index={img_tok},
    # grid_hw / num_prefix_tokens / hidden_dim: from section [2]
    # vision_feature_layer / _select_strategy: from section [3] (MAIRA-2 keeps CLS => 'full', -1)
    image_block_order=("current_frontal", "prior_frontal"),
    quant_skip_modules=("{vt_attr}", "{proj_attr}"),
)""")
    print("-" * 72)
    print("done.")


if __name__ == "__main__":
    main()
