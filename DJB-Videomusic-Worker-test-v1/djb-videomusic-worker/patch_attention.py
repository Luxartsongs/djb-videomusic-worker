"""DJB modification: use native PyTorch SDPA if no FlashAttention is installed.
The rest of the official Wan attention implementation remains unchanged.
"""
from pathlib import Path
p = Path('/app/Wan2.2/wan/modules/attention.py')
s = p.read_text()
marker = '    half_dtypes = (torch.float16, torch.bfloat16)'
assert s.count(marker) == 1, 'Unexpected upstream attention code'
fallback = '''    if not FLASH_ATTN_2_AVAILABLE and not FLASH_ATTN_3_AVAILABLE:
        # Input [batch, sequence, heads, dimension]. Keep key-padding masks.
        qq = q.transpose(1, 2).to(dtype)
        kk = k.transpose(1, 2).to(dtype)
        vv = v.transpose(1, 2).to(dtype)
        if q_scale is not None:
            qq = qq * q_scale
        mask = None
        if k_lens is not None:
            positions = torch.arange(k.shape[1], device=k.device)
            mask = positions[None, :] < k_lens.to(k.device)[:, None]
            mask = mask[:, None, None, :]
        out = torch.nn.functional.scaled_dot_product_attention(
            qq, kk, vv, attn_mask=mask, dropout_p=dropout_p,
            is_causal=causal, scale=softmax_scale)
        return out.transpose(1, 2).contiguous().to(q.dtype)

'''
p.write_text(s.replace(marker, fallback + marker))
# This worker exposes only image-to-video. Avoid importing optional speech and
# animation stacks from the upstream package initializer.
init = Path('/app/Wan2.2/wan/__init__.py')
init.write_text('from . import configs, distributed, modules\nfrom .image2video import WanI2V\n')
