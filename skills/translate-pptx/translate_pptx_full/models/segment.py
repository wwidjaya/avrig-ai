from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Optional


class ElementType(Enum):
    RUN = auto()
    TABLE_CELL_RUN = auto()
    CHART_TITLE_RUN = auto()
    AXIS_TITLE_RUN = auto()
    NOTE_RUN = auto()
    COMMENT_TEXT = auto()
    SMARTART_PLACEHOLDER = auto()
    # paragraph-level (multi-run) segment types
    PARAGRAPH = auto()
    TABLE_CELL = auto()
    CHART_TITLE = auto()
    AXIS_TITLE = auto()
    NOTE = auto()


@dataclass
class FontSnapshot:
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    size_pt: Optional[float] = None
    color_rgb: Optional[str] = None
    name: Optional[str] = None


@dataclass
class TextSegment:
    id: str
    slide_idx: int
    shape_id: int
    para_idx: int
    run_idx: int
    original_text: str
    element_type: ElementType
    location_hint: list = field(default_factory=list)
    formatting: Optional[FontSnapshot] = None
    translated_text: Optional[str] = None
    skip: bool = False
    leading_ws: str = ""
    trailing_ws: str = ""

    def to_dict(self):
        d = asdict(self)
        d["element_type"] = self.element_type.name
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["element_type"] = ElementType[d["element_type"]]
        if d.get("formatting"):
            d["formatting"] = FontSnapshot(**d["formatting"])
        return cls(**d)
