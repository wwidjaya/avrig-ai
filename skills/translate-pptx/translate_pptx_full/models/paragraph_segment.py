from dataclasses import dataclass, field, asdict
from typing import Optional

from .segment import ElementType


@dataclass
class RunInfo:
    """Metadata for a single run within a paragraph (extraction-time snapshot)."""

    run_idx: int
    text: str                 # raw text including whitespace
    leading_ws: str           # leading whitespace (from original run)
    trailing_ws: str          # trailing whitespace (from original run)
    char_len: int
    word_count: int           # words in stripped text (0 for whitespace-only runs)
    formatting: Optional[dict] = None   # FontSnapshot dict

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class ParagraphSegment:
    """A full paragraph as the translation unit, with per-run metadata for splitting."""

    id: str
    slide_idx: int
    shape_id: int
    para_idx: int
    full_text: str            # merged raw text of all runs (may have trailing ws)
    element_type: ElementType
    runs: list = field(default_factory=list)          # list[RunInfo], ordered
    location_hint: list = field(default_factory=list)
    translated_text: Optional[str] = None
    skip: bool = False

    @property
    def original_text(self) -> str:
        return self.full_text

    def to_dict(self):
        d = asdict(self)
        d["element_type"] = self.element_type.name
        d["runs"] = [r.to_dict() for r in self.runs]
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["element_type"] = ElementType[d["element_type"]]
        d["runs"] = [RunInfo.from_dict(r) for r in d.get("runs", [])]
        return cls(**d)
