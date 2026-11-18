"""Shared text/font helpers for the translation pipeline."""

import re

_SKIP_RE = re.compile(
    r'^[\d\s\-–—.,;:!?/\\()\[\]{}<>""''\u00ab\u00bb\u00b7\u2022\u25cf\u25a0\u25b2\u25bc\u25b6\u25c0\u25cb\u2605\u2606\u2666\u25c6\u25d8\u2713\u2717\u2718+=*^%$#@&~`|\u00a0\u2000-\u200f\u2028-\u202f]+$'
)


def should_translate(text: str) -> bool:
    """True if the text contains translatable content (not just numbers/punct/whitespace)."""
    s = text.strip()
    if not s:
        return False
    return not _SKIP_RE.match(s)


def snapshot_font(run) -> dict:
    """Capture run font properties safely (handles _NoneColor)."""
    f = run.font
    color = None
    try:
        if f.color and f.color.rgb:
            color = str(f.color.rgb)
    except AttributeError:
        pass
    return {
        "bold": f.bold,
        "italic": f.italic,
        "underline": f.underline,
        "size_pt": f.size.pt if f.size else None,
        "color_rgb": color,
        "name": f.name,
    }
