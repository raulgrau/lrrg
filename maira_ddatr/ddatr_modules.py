"""
DDaTR difference-aware modules, ported to MAIRA-2 / RAD-DINO geometry.

Source ops are lifted (not reimplemented from equations) from
    DDaTR: Dynamic Difference-aware Temporal Residual Network
    Song, Tang, Yang, Li. IEEE TMI 2025. arXiv:2505.03401
    https://github.com/xmed-lab/DDaTR  (models/resnet.py)
which in turn builds on LAVT (PWAM / SpatialImageLanguageAttention) and
LDCNet (the learnable descriptive convolution, conv3x3_learn).

Naming map (paper  ->  repo class  ->  this file):
    DFAM   (report->prior-image alignment)   = PWAM + gate            -> `DFAM`
    DDAM   (difference-aware current enh.)    = FeatureFusion + gate   -> `DDAM`
    LDConv (learnable descriptive conv)       = conv3x3_learn          -> `LDConv`

KEY ADAPTATIONS vs. the original repo
-------------------------------------
1. The repo runs on a Swin-B backbone with 4 stages and channel widths
   [128,256,512,1024] over down-sampling spatial maps. RAD-DINO-MAIRA-2 is a
   single-scale ViT-B/14: hidden dim 768, 518/14 = 37x37 = 1369 patch tokens.
   So every module here is fixed at C=768 and operates on a 37x37 grid.
2. `conv3x3_learn` hard-coded `.cuda()` for its center mask. We register it as a
   (non-persistent) buffer so the op is device-agnostic (CPU test / CUDA train).
3. The repo's LDC blocks use BatchNorm2d. We train at batch_size 1-2, where BN is
   degenerate (zero/with-unstable running stats). Default norm is GroupNorm; set
   norm="batch" to reproduce the original exactly.

Tensor conventions used throughout this file
    patch sequence : (B, N, C)         with N = H*W = 1369, C = 768
    spatial grid   : (B, C, H, W)      with H = W = 37
    text features  : (B, L, C_txt)     + bool/float mask (B, L)
    has_prior      : (B,) float in {0,1}; 0 -> every fusion residual is gated to
                     zero, so the stream degrades to vanilla RAD-DINO (this is the
                     repo's `has_progress` / `n=1` missing-prior case).
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def seq_to_grid(seq: torch.Tensor, h: int, w: int) -> torch.Tensor:
    """(B, H*W, C) -> (B, C, H, W)."""
    b, n, c = seq.shape
    assert n == h * w, f"seq len {n} != {h}*{w}"
    return seq.transpose(1, 2).reshape(b, c, h, w)


def grid_to_seq(grid: torch.Tensor) -> torch.Tensor:
    """(B, C, H, W) -> (B, H*W, C)."""
    b, c, h, w = grid.shape
    return grid.flatten(2).transpose(1, 2)


def _safe_groups(channels: int, max_groups: int = 32) -> int:
    """Largest divisor of `channels` that is <= max_groups (>=1)."""
    g = min(max_groups, channels)
    while channels % g != 0:
        g -= 1
    return max(1, g)


def _make_gate(dim: int) -> nn.Sequential:
    """Tanh gate MLP exactly as in the repo's `gate` / `context_gate`."""
    return nn.Sequential(
        nn.Linear(dim, dim, bias=False),
        nn.ReLU(),
        nn.Linear(dim, dim, bias=False),
        nn.Tanh(),
    )


# --------------------------------------------------------------------------- #
# LDConv  (== conv3x3_learn, from LDCNet via DDaTR)
# --------------------------------------------------------------------------- #
class LDConv(nn.Module):
    """Learnable Descriptive Convolution (central-difference 3x3).

    Ported verbatim from DDaTR/models/resnet.py::conv3x3_learn with the single
    change that `center_mask` is a registered buffer instead of `.cuda()`.
    The kernel is fixed at 3x3 because the central-difference mask is defined for
    a 3x3 neighbourhood.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        stride: int = 1,
        padding: int = 1,
        dilation: int = 1,
        groups: int = 1,
        bias: bool = False,
        theta: float = 0.5,
    ) -> None:
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, stride=stride,
            padding=padding, dilation=dilation, groups=groups, bias=bias,
        )
        center = torch.tensor(
            [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]]
        )
        self.register_buffer("center_mask", center, persistent=False)
        self.register_buffer(
            "base_mask", torch.ones_like(self.conv.weight), persistent=False
        )
        # one learnable scalar per (out, in/groups) filter, plus a global theta
        self.learnable_mask = nn.Parameter(
            torch.ones(self.conv.weight.size(0), self.conv.weight.size(1))
        )
        self.learnable_theta = nn.Parameter(torch.ones(1) * theta)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # subtract a theta-weighted, per-filter share of the kernel sum from the
        # center tap -> "descriptive" / difference-sensitive convolution
        kernel_sum = self.conv.weight.sum(2).sum(2)[:, :, None, None]
        mask = (
            self.base_mask
            - self.learnable_theta
            * self.learnable_mask[:, :, None, None]
            * self.center_mask
            * kernel_sum
        )
        return F.conv2d(
            x,
            self.conv.weight * mask,
            self.conv.bias,
            stride=self.conv.stride,
            padding=self.conv.padding,
            dilation=self.conv.dilation,
            groups=self.conv.groups,
        )


class _LDCBlock(nn.Module):
    """LDConv -> Norm -> ReLU, the building block used inside DDAM."""

    def __init__(self, dim: int, norm: str = "group") -> None:
        super().__init__()
        self.ldc = LDConv(dim, dim)
        if norm == "batch":
            self.norm = nn.BatchNorm2d(dim)
        elif norm == "group":
            self.norm = nn.GroupNorm(_safe_groups(dim), dim)
        elif norm == "none":
            self.norm = nn.Identity()
        else:
            raise ValueError(f"unknown norm '{norm}'")
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.norm(self.ldc(x)))


# --------------------------------------------------------------------------- #
# Language-aware attention (== SpatialImageLanguageAttention + PWAM, from LAVT)
# --------------------------------------------------------------------------- #
class _SpatialImageLanguageAttention(nn.Module):
    """Image-as-query / text-as-key-value cross attention (LAVT).

    Ported from DDaTR/models/resnet.py::SpatialImageLanguageAttention.
    Inputs:
        x      : image sequence (B, N, C_v)
        l      : text, channels-first (B, C_l, L)
        l_mask : (B, L, 1)  (1 = keep, 0 = pad)
    Output:
        (B, N, value_channels)
    """

    def __init__(self, v_in: int, l_in: int, key_ch: int, value_ch: int,
                 out_ch: int | None = None, num_heads: int = 1) -> None:
        super().__init__()
        self.key_channels = key_ch
        self.value_channels = value_ch
        self.num_heads = num_heads
        self.out_channels = out_ch if out_ch is not None else value_ch
        assert key_ch % num_heads == 0 and value_ch % num_heads == 0

        self.f_key = nn.Conv1d(l_in, key_ch, 1)
        self.f_query = nn.Sequential(nn.Conv1d(v_in, key_ch, 1),
                                     nn.InstanceNorm1d(key_ch))
        self.f_value = nn.Conv1d(l_in, value_ch, 1)
        self.W = nn.Sequential(nn.Conv1d(value_ch, self.out_channels, 1),
                               nn.InstanceNorm1d(self.out_channels))

    def forward(self, x: torch.Tensor, l: torch.Tensor, l_mask: torch.Tensor) -> torch.Tensor:
        B, N = x.size(0), x.size(1)
        x = x.permute(0, 2, 1)            # (B, C_v, N)
        l_mask = l_mask.permute(0, 2, 1)  # (B, 1, L)

        query = self.f_query(x).permute(0, 2, 1)          # (B, N, key)
        key = self.f_key(l) * l_mask                      # (B, key, L)
        value = self.f_value(l) * l_mask                  # (B, value, L)
        n_l = value.size(-1)

        query = query.reshape(B, N, self.num_heads, self.key_channels // self.num_heads).permute(0, 2, 1, 3)
        key = key.reshape(B, self.num_heads, self.key_channels // self.num_heads, n_l)
        value = value.reshape(B, self.num_heads, self.value_channels // self.num_heads, n_l)
        l_mask = l_mask.unsqueeze(1)                      # (B, 1, 1, L)

        sim = (self.key_channels ** -0.5) * torch.matmul(query, key)   # (B, heads, N, L)
        sim = sim + (1e4 * l_mask - 1e4)
        sim = F.softmax(sim, dim=-1)

        out = torch.matmul(sim, value.permute(0, 1, 3, 2))            # (B, heads, N, value/heads)
        out = out.permute(0, 2, 1, 3).contiguous().reshape(B, N, self.value_channels)
        out = self.W(out.permute(0, 2, 1)).permute(0, 2, 1)           # (B, N, out)
        return out


class _PWAM(nn.Module):
    """Pixel-Word Attention Module (LAVT) -> DDaTR/models/resnet.py::PWAM."""

    def __init__(self, dim: int, v_in: int, l_in: int, key_ch: int,
                 value_ch: int, num_heads: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.vis_project = nn.Sequential(nn.Conv1d(dim, dim, 1), nn.GELU(), nn.Dropout(dropout))
        self.image_lang_att = _SpatialImageLanguageAttention(
            v_in, l_in, key_ch, value_ch, out_ch=value_ch, num_heads=num_heads)
        self.project_mm = nn.Sequential(nn.Conv1d(value_ch, value_ch, 1), nn.GELU(), nn.Dropout(dropout))

    def forward(self, x: torch.Tensor, l: torch.Tensor, l_mask: torch.Tensor) -> torch.Tensor:
        vis = self.vis_project(x.permute(0, 2, 1))             # (B, C, N)
        lang = self.image_lang_att(x, l, l_mask).permute(0, 2, 1)  # (B, C, N)
        mm = self.project_mm(vis * lang)                       # (B, C, N)
        return mm.permute(0, 2, 1)                             # (B, N, C)


# --------------------------------------------------------------------------- #
# DFAM : report -> prior-image alignment  (PWAM + Tanh gate)
# --------------------------------------------------------------------------- #
class DFAM(nn.Module):
    """Difference-aware Feature Alignment Module.

    Injects the prior *report* (text) into the prior *image* features via
    image-as-query cross attention, then a gated residual. Output is image-driven
    (text only re-weights), matching the repo's `context_fusion` + `context_gate`.

    forward:
        img_seq : (B, N, C)   prior-image patch tokens
        txt     : (B, L, C_txt) prior-report token features
        txt_mask: (B, L) float/bool
        has_prior: (B,)
    returns the GATED RESIDUAL (B, N, C); caller adds it to img_seq.
    """

    def __init__(self, dim: int = 768, txt_dim: int = 768, num_heads: int = 12) -> None:
        super().__init__()
        self.pwam = _PWAM(dim, v_in=dim, l_in=txt_dim, key_ch=dim,
                          value_ch=dim, num_heads=num_heads)
        self.gate = _make_gate(dim)

    def forward(self, img_seq, txt, txt_mask, has_prior):
        txt_cf = txt.permute(0, 2, 1)                 # (B, C_txt, L)
        l_mask = txt_mask.to(img_seq.dtype).unsqueeze(-1)  # (B, L, 1)
        residual = self.pwam(img_seq, txt_cf, l_mask)      # (B, N, C)
        alpha = self.gate(residual) * has_prior.view(-1, 1, 1).to(img_seq.dtype)
        return alpha * residual


# --------------------------------------------------------------------------- #
# DDAM : difference-aware current enhancement  (FeatureFusion + Tanh gate)
# --------------------------------------------------------------------------- #
class DDAM(nn.Module):
    """Dynamic Difference-aware Module.

    Consumes current features + aligned-prior features, builds a channel-wise
    difference gate via two LDConv branches, and returns a gated residual that
    carries interval-change information into the current stream. Ported from
    DDaTR/models/resnet.py::FeatureFusion (+ the repo's `gate`).

    forward:
        cur_grid   : (B, C, H, W)
        prior_grid : (B, C, H, W)  (already DFAM-aligned & at matched depth)
        has_prior  : (B,)
    returns the GATED RESIDUAL in sequence form (B, N=H*W, C); caller adds it.
    """

    def __init__(self, dim: int = 768, norm: str = "group") -> None:
        super().__init__()
        self.ldc_cur = _LDCBlock(dim, norm)
        self.ldc_prior = _LDCBlock(dim, norm)
        self.diff_attn = nn.Sequential(nn.AdaptiveAvgPool2d((1, 1)), nn.Sigmoid())
        self.fc = nn.Linear(dim * 2, dim)
        self.gate = _make_gate(dim)

    def forward(self, cur_grid, prior_grid, has_prior):
        b, c, h, w = cur_grid.shape
        e_cur = self.ldc_cur(cur_grid)                 # (B, C, H, W)
        e_prior = self.ldc_prior(prior_grid)
        diff = self.diff_attn(e_cur - e_prior)         # (B, C, 1, 1) channel gate
        f_cur = e_cur * diff
        f_prior = e_prior * diff
        cat = torch.cat([f_cur, f_prior], dim=1)       # (B, 2C, H, W)
        res = self.fc(grid_to_seq(cat))                # (B, N, C)
        alpha = self.gate(res) * has_prior.view(-1, 1, 1).to(cur_grid.dtype)
        return alpha * res                             # (B, N, C)


# --------------------------------------------------------------------------- #
# DDaTRBlock : one injection point = DFAM (prior stream) + DDAM (current stream)
# --------------------------------------------------------------------------- #
class DDaTRBlock(nn.Module):
    """A single encoder injection point.

    Split into two entry points so the encoder can run the *prior stream first*
    (caching aligned-prior features at each depth) and then the *current stream*
    (consuming the cache). This is mathematically identical to the repo's
    interleaved two-stream forward because the flow is strictly prior->current:
    the prior alignment never depends on the current image.
    """

    def __init__(self, dim: int = 768, txt_dim: int = 768,
                 num_heads: int = 12, norm: str = "group") -> None:
        super().__init__()
        self.dfam = DFAM(dim, txt_dim, num_heads)
        self.ddam = DDAM(dim, norm)

    def align_prior(self, prior_seq, txt, txt_mask, has_prior):
        """Prior stream: residually align prior-image tokens with prior report."""
        return prior_seq + self.dfam(prior_seq, txt, txt_mask, has_prior)

    def enhance_current(self, cur_seq, prior_seq_aligned, has_prior, h, w):
        """Current stream: residually inject prior->current difference."""
        cur_grid = seq_to_grid(cur_seq, h, w)
        prior_grid = seq_to_grid(prior_seq_aligned, h, w)
        return cur_seq + self.ddam(cur_grid, prior_grid, has_prior)


# --------------------------------------------------------------------------- #
# self-test (CPU): shapes, gating no-op, and gradient flow to DFAM & DDAM
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    torch.manual_seed(0)
    B, H, W, C, L, Ctxt = 2, 37, 37, 768, 24, 768
    N = H * W
    block = DDaTRBlock(dim=C, txt_dim=Ctxt, num_heads=12, norm="group")

    cur_seq = torch.randn(B, N, C, requires_grad=True)
    prior_seq = torch.randn(B, N, C, requires_grad=True)
    txt = torch.randn(B, L, Ctxt)
    txt_mask = torch.ones(B, L)
    has_prior = torch.tensor([1.0, 1.0])

    aligned = block.align_prior(prior_seq, txt, txt_mask, has_prior)
    enhanced = block.enhance_current(cur_seq, aligned, has_prior, H, W)
    assert aligned.shape == (B, N, C), aligned.shape
    assert enhanced.shape == (B, N, C), enhanced.shape
    print("[ok] shapes:", tuple(aligned.shape), tuple(enhanced.shape))

    # missing-prior must be a no-op: enhanced == cur_seq exactly when has_prior=0
    hp0 = torch.zeros(B)
    aligned0 = block.align_prior(prior_seq, txt, txt_mask, hp0)
    enh0 = block.enhance_current(cur_seq, aligned0, hp0, H, W)
    assert torch.allclose(aligned0, prior_seq, atol=1e-6), "DFAM not a no-op at has_prior=0"
    assert torch.allclose(enh0, cur_seq, atol=1e-6), "DDAM not a no-op at has_prior=0"
    print("[ok] has_prior=0 is an exact no-op (vanilla RAD-DINO passthrough)")

    # gradient flow reaches both DFAM and DDAM params
    enhanced.sum().backward()
    g_dfam = block.dfam.pwam.image_lang_att.f_query[0].weight.grad
    g_ddam = block.ddam.fc.weight.grad
    assert g_dfam is not None and g_dfam.abs().sum() > 0, "no grad into DFAM"
    assert g_ddam is not None and g_ddam.abs().sum() > 0, "no grad into DDAM"
    print("[ok] gradients flow into DFAM and DDAM")

    n_params = sum(p.numel() for p in block.parameters() if p.requires_grad)
    print(f"[ok] trainable params in one DDaTRBlock: {n_params/1e6:.2f}M")
