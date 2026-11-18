from dataclasses import dataclass, field
from typing import Optional

from .segment import TextSegment
from .paragraph_segment import ParagraphSegment


@dataclass
class TranslationManifest:
    source_path: str
    segments: list = field(default_factory=list)
    translations: dict = field(default_factory=dict)
    unit: str = "paragraph"        # "run" or "paragraph"

    def add_segment(self, seg):
        self.segments.append(seg)

    def get_translated(self, seg_id: str) -> Optional[str]:
        return self.translations.get(seg_id)

    def set_translation(self, seg_id: str, text: str):
        self.translations[seg_id] = text

    def to_dict(self):
        return {
            "source_path": self.source_path,
            "unit": self.unit,
            "segments": [s.to_dict() for s in self.segments],
            "translations": self.translations,
        }

    @classmethod
    def from_dict(cls, d):
        m = cls(source_path=d["source_path"], unit=d.get("unit", "run"))
        if m.unit == "paragraph":
            m.segments = [ParagraphSegment.from_dict(s) for s in d["segments"]]
        else:
            m.segments = [TextSegment.from_dict(s) for s in d["segments"]]
        m.translations = d.get("translations", {})
        return m

    def total_segments(self) -> int:
        return len(self.segments)

    def translated_count(self) -> int:
        return sum(1 for s in self.segments if s.translated_text)

    def skipped_count(self) -> int:
        return sum(1 for s in self.segments if s.skip)
