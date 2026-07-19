"""
InjectedRadDino: wrap RAD-DINO-MAIRA-2 (an HF Dinov2 ViT-B/14) so that DDaTR
difference-aware fusion happens *inside the visual encoder*, between transformer
blocks, rather than at the LLM (MAIRA-2's native late fusion of the prior).

Why this shape
--------------
RAD-DINO is single-scale, so we treat groups of ViT blocks as pseudo-"stages":
inject DDaTR at a configurable set of block indices.
    M1 (lightest)  : inject at the final block only  -> {11} for a 12-layer ViT
    M2 (multiscale): inject at {3,6,9,12} (1-indexed) -> blocks {2,5,8,11}

Two-pass, prior-first-cache execution
-------------------------------------
The prior alignment (DFAM) depends only on the prior image + prior report, never
on the current image, and the flow is strictly prior->current. So we can:
    pass 1  run the prior image through the ViT, applying DFAM at each injection
            point (updating the prior stream in place) and caching the aligned
            prior patch tokens at that depth;
    pass 2  run the current image through the ViT, applying DDAM at each injection
            point using the cached aligned-prior tokens.
This is identical to the repo's interleaved two-stream forward but lets us free
the prior stream's compute graph is *kept* (DFAM must receive gradients), yet we
never hold two live ViT forwards at once.

Missing prior
-------------
`has_prior[i] == 0` gates every fusion residual to zero (see ddatr_modules), so
the current stream for that sample is exactly vanilla RAD-DINO. If *no* sample in
the batch has a prior, pass 1 is skipped entirely.

Interface assumptions (HF Dinov2Model) -- verify once on the cluster with
probe_processor.py / a dir() on the loaded model:
    vision_tower.embeddings(pixel_values) -> (B, P+N, C)
    vision_tower.encoder.layer            -> ModuleList of blocks; block(h) -> (h, ...)
    vision_tower.layernorm                -> final LayerNorm
    P = num_prefix_tokens = 1 (CLS; RAD-DINO-MAIRA-2 has no register tokens:
        1 + 37*37 = 1370 total tokens)
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn

from ddatr_modules import DDaTRBlock


def resolve_injection_indices(spec: str | list[int], num_layers: int) -> list[int]:
    """Turn an injection spec into sorted 0-indexed block indices.

    spec="M1"            -> [num_layers-1]
    spec="M2"            -> evenly spaced quartile blocks, e.g. 12 layers -> [2,5,8,11]
    spec=[3,6,9,12]      -> 1-indexed list -> [2,5,8,11]
    spec=[2,5,8,11]      -> already 0-indexed if max < num_layers and min==... ambiguous;
                            to avoid ambiguity, ALWAYS pass 1-indexed lists or M1/M2.
    """
    if isinstance(spec, str):
        s = spec.upper()
        if s in ("NONE", "OFF", ""):
            return []                       # no DDaTR at all (fine-tuned baseline)
        if s == "M1":
            return [num_layers - 1]
        if s == "M2":
            return [round(num_layers * q / 4) - 1 for q in (1, 2, 3, 4)]
        raise ValueError(f"unknown injection spec '{spec}' (use 'none','M1','M2', or a 1-indexed list)")
    # explicit list, interpreted as 1-indexed block numbers
    idx = sorted({int(i) - 1 for i in spec})
    for i in idx:
        if not (0 <= i < num_layers):
            raise ValueError(f"injection block {i+1} out of range for {num_layers} layers")
    return idx


class InjectedRadDino(nn.Module):
    def __init__(
        self,
        vision_tower: nn.Module,
        injection: str | list[int] = "M1",
        *,
        embeddings_attr: str = "embeddings",
        layers_path: tuple[str, str] = ("encoder", "layer"),
        layernorm_attr: str = "layernorm",
        num_prefix_tokens: int = 1,
        grid_hw: tuple[int, int] = (37, 37),
        hidden_dim: int = 768,
        txt_dim: int = 768,
        num_heads: int = 12,
        norm: str = "group",
    ) -> None:
        super().__init__()
        self.vt = vision_tower
        self.embeddings = getattr(vision_tower, embeddings_attr)
        mod = vision_tower
        for name in layers_path:
            mod = getattr(mod, name)
        self.layers: nn.ModuleList = mod
        self.layernorm = getattr(vision_tower, layernorm_attr, nn.Identity())

        self.P = num_prefix_tokens
        self.H, self.W = grid_hw
        self.N = self.H * self.W
        self.num_layers = len(self.layers)

        self.injection_indices = resolve_injection_indices(injection, self.num_layers)
        # one DDaTRBlock per injection point, addressed by block index
        self.blocks = nn.ModuleDict(
            {str(i): DDaTRBlock(hidden_dim, txt_dim, num_heads, norm)
             for i in self.injection_indices}
        )
        # Nothing trainable lives before the shallowest injection point (the ViT
        # itself is frozen), so no backward graph is needed there -- gradients
        # only need to reach as far back as this depth. For M1 (injection at the
        # final block only) this skips backprop bookkeeping for 11 of 12 blocks,
        # in BOTH the prior and current passes. See _encode_prior/_encode_current.
        # injection="none": no DDaTR at all -> the whole ViT runs under no_grad
        # (first_injection == num_layers), a pure vanilla RAD-DINO forward. Used
        # for the fine-tuned-without-DDaTR baseline (prior via native late fusion).
        self.first_injection = min(self.injection_indices) if self.injection_indices \
            else self.num_layers

    # ----- internal: run one block (handles tuple/tensor return) ----------- #
    @staticmethod
    def _run_layer(layer: nn.Module, hidden: torch.Tensor) -> torch.Tensor:
        out = layer(hidden)
        return out[0] if isinstance(out, tuple) else out

    def _split(self, hidden: torch.Tensor):
        return hidden[:, : self.P], hidden[:, self.P :]

    # ----- pass 1: prior stream, cache aligned-prior patch tokens ---------- #
    def _encode_prior(self, prior_pixels, txt, txt_mask, has_prior) -> dict[int, torch.Tensor]:
        hidden = self.embeddings(prior_pixels)
        assert hidden.shape[1] == self.P + self.N, (
            f"token count {hidden.shape[1]} != prefix {self.P} + patches {self.N}; "
            "check num_prefix_tokens / grid_hw against your RAD-DINO build"
        )
        # Blocks before the shallowest injection are frozen with nothing
        # downstream needing their activation-gradients -- run them with no
        # autograd graph at all. Values are identical either way.
        with torch.no_grad():
            for i in range(self.first_injection):
                hidden = self._run_layer(self.layers[i], hidden)
        cache: dict[int, torch.Tensor] = {}
        for i in range(self.first_injection, self.num_layers):
            hidden = self._run_layer(self.layers[i], hidden)
            if i in self.injection_indices:
                prefix, patches = self._split(hidden)
                patches = self.blocks[str(i)].align_prior(patches, txt, txt_mask, has_prior)
                cache[i] = patches  # NOT detached: DFAM needs gradients
                hidden = torch.cat([prefix, patches], dim=1)
        return cache

    # ----- pass 2: current stream, consume cache --------------------------- #
    def _encode_current(self, cur_pixels, prior_cache, has_prior):
        hidden = self.embeddings(cur_pixels)
        all_hidden = [hidden]
        with torch.no_grad():
            for i in range(self.first_injection):
                hidden = self._run_layer(self.layers[i], hidden)
                all_hidden.append(hidden)
        for i in range(self.first_injection, self.num_layers):
            hidden = self._run_layer(self.layers[i], hidden)
            if i in self.injection_indices:
                prefix, patches = self._split(hidden)
                prior_patches = prior_cache[i]
                patches = self.blocks[str(i)].enhance_current(
                    patches, prior_patches, has_prior, self.H, self.W)
                hidden = torch.cat([prefix, patches], dim=1)
            all_hidden.append(hidden)
        last = self.layernorm(hidden)
        return last, all_hidden

    def forward(
        self,
        cur_pixels: torch.Tensor,
        prior_pixels: Optional[torch.Tensor],
        txt: Optional[torch.Tensor],
        txt_mask: Optional[torch.Tensor],
        has_prior: Optional[torch.Tensor],
    ):
        """Returns (last_hidden_state, hidden_states_tuple).

        hidden_states_tuple follows HF convention: [embeddings_out, after_layer_0,
        ..., after_layer_{L-1}], pre-final-LN, so a LLaVA-style feature selector
        can index e.g. -2. `last_hidden_state` is post-final-LN.
        """
        B = cur_pixels.shape[0]
        if has_prior is None:
            has_prior = torch.zeros(B, device=cur_pixels.device)

        # injection="none": no DDaTR blocks -> skip the prior pass entirely and
        # return a pure vanilla RAD-DINO forward of the current image.
        if not self.injection_indices:
            last, all_hidden = self._encode_current(cur_pixels, {}, has_prior)
            return last, tuple(all_hidden)

        any_prior = bool((has_prior > 0).any().item()) and prior_pixels is not None
        if any_prior:
            cache = self._encode_prior(prior_pixels, txt, txt_mask, has_prior)
        else:
            # no prior anywhere -> zero cache; DDAM residuals are gated to 0 anyway
            cache = {i: torch.zeros(B, self.N, self.blocks[str(i)].dfam.gate[0].in_features,
                                    device=cur_pixels.device, dtype=cur_pixels.dtype)
                     for i in self.injection_indices}

        last, all_hidden = self._encode_current(cur_pixels, cache, has_prior)
        return last, tuple(all_hidden)


# --------------------------------------------------------------------------- #
# self-test (CPU) with a stub ViT that mimics the HF Dinov2 interface
# --------------------------------------------------------------------------- #
class _StubEmbeddings(nn.Module):
    def __init__(self, c, p, n):
        super().__init__()
        self.c, self.p, self.n = c, p, n
        self.proj = nn.Conv2d(3, c, kernel_size=14, stride=14)
        self.cls = nn.Parameter(torch.randn(1, p, c))

    def forward(self, pixels):
        # pixels: (B,3,518,518) -> (B, c, 37,37) -> (B, n, c) ; prepend p prefix tokens
        x = self.proj(pixels).flatten(2).transpose(1, 2)  # (B, n, c)
        b = x.shape[0]
        return torch.cat([self.cls.expand(b, -1, -1), x], dim=1)


class _StubBlock(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.ln = nn.LayerNorm(c)
        self.mlp = nn.Sequential(nn.Linear(c, c), nn.GELU(), nn.Linear(c, c))

    def forward(self, h):
        return (h + self.mlp(self.ln(h)),)  # tuple, like Dinov2Layer


class _StubEncoder(nn.Module):
    def __init__(self, c, depth):
        super().__init__()
        self.layer = nn.ModuleList([_StubBlock(c) for _ in range(depth)])


class _StubViT(nn.Module):
    def __init__(self, c=768, p=1, n=37 * 37, depth=12):
        super().__init__()
        self.embeddings = _StubEmbeddings(c, p, n)
        self.encoder = _StubEncoder(c, depth)
        self.layernorm = nn.LayerNorm(c)


if __name__ == "__main__":
    import gc
    torch.manual_seed(0)
    B, C, P, depth, L = 2, 768, 1, 12, 24
    vit = _StubViT(C, P, 37 * 37, depth)

    # M2 and [3,6,9,12] resolve to identical indices; test M1 + M2 only.
    for spec in ("M1", "M2"):
        inj = InjectedRadDino(vit, injection=spec, num_prefix_tokens=P,
                              grid_hw=(37, 37), hidden_dim=C, txt_dim=C, num_heads=12)
        print(f"\nspec={spec!r} -> injection blocks (0-idx) {inj.injection_indices}")

        cur = torch.randn(B, 3, 518, 518)
        prior = torch.randn(B, 3, 518, 518)
        txt = torch.randn(B, L, C)
        txt_mask = torch.ones(B, L)
        has_prior = torch.tensor([1.0, 0.0])  # sample 0 has prior, sample 1 does not

        last, hs = inj(cur, prior, txt, txt_mask, has_prior)
        assert last.shape == (B, P + 37 * 37, C), last.shape
        assert len(hs) == depth + 1
        print(f"  last_hidden {tuple(last.shape)}  | n hidden states {len(hs)}")

        # sample with has_prior=0 must match a vanilla (no-fusion) forward exactly
        with torch.no_grad():
            # vanilla forward of the stub on sample 1 only
            h = vit.embeddings(cur[1:2])
            for layer in vit.encoder.layer:
                h = layer(h)[0]
            vanilla = vit.layernorm(h)
        assert torch.allclose(last[1:2], vanilla, atol=1e-5), "has_prior=0 sample diverged from vanilla"
        print("  [ok] has_prior=0 sample == vanilla RAD-DINO forward")

        # gradient flows into the injected DDaTR blocks
        last.sum().backward()
        any_grad = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in inj.blocks.parameters()
        )
        assert any_grad, "no gradient into injected DDaTR blocks"
        print("  [ok] gradient flows into injected blocks")
        del inj, last, hs, cur, prior, txt
        vit.zero_grad(set_to_none=True)
        gc.collect()

    # injection="none": no DDaTR blocks -> pure vanilla RAD-DINO forward, for the
    # fine-tuned-without-DDaTR baseline. Prior is ignored by the encoder (it goes
    # via the LLM prompt in keep_as_tokens mode instead).
    inj0 = InjectedRadDino(vit, injection="none", num_prefix_tokens=P,
                           grid_hw=(37, 37), hidden_dim=C, txt_dim=C, num_heads=12)
    assert inj0.injection_indices == [], inj0.injection_indices
    assert len(inj0.blocks) == 0
    cur = torch.randn(B, 3, 518, 518)
    last0, hs0 = inj0(cur, None, None, None, torch.zeros(B))
    with torch.no_grad():
        h = vit.embeddings(cur)
        for layer in vit.encoder.layer:
            h = layer(h)[0]
        vanilla = vit.layernorm(h)
    assert torch.allclose(last0, vanilla, atol=1e-5), "injection=none diverged from vanilla"
    print("\nspec='none' -> no injection")
    print("  [ok] injection=none == vanilla RAD-DINO forward (prior ignored by encoder)")
