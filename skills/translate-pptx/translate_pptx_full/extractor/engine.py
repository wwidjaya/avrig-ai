from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from ..models.segment import TextSegment, FontSnapshot, ElementType
from .shapes import extract_shape_runs
from .tables import extract_table_runs
from .charts import extract_chart_runs
from .groups import extract_group_runs
from .notes import extract_notes_runs
from .smartart import extract_smartart

CMT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


def extract_all(pptx_path: str, logger=None) -> list[TextSegment]:
    prs = Presentation(str(pptx_path))
    segments = []

    for slide_idx, slide in enumerate(prs.slides):
        if logger:
            logger.debug(f"  Slide {slide_idx + 1}/{len(prs.slides)}")
        for shape in slide.shapes:
            _extract_shape(shape, slide_idx, segments)

        notes_segs = extract_notes_runs(slide, slide_idx)
        segments.extend(notes_segs)

    comment_segs = _extract_comments(prs)
    segments.extend(comment_segs)

    if logger:
        logger.info(f"Extracted {len(segments)} run-level segments")
    return segments


def _extract_shape(shape, slide_idx: int, segments: list, location_hint: list = None):
    hint = list(location_hint) if location_hint else []

    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        segs = extract_group_runs(shape, slide_idx, hint)
        segments.extend(segs)

    elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
        segs = extract_table_runs(shape, slide_idx, shape.shape_id, hint)
        segments.extend(segs)

    elif shape.shape_type == MSO_SHAPE_TYPE.CHART:
        segs = extract_chart_runs(shape, slide_idx, shape.shape_id, hint)
        segments.extend(segs)

    elif shape.shape_type == MSO_SHAPE_TYPE.DIAGRAM:
        segs = extract_smartart(shape, slide_idx, shape.shape_id, hint)
        segments.extend(segs)

    elif shape.has_text_frame:
        segs = extract_shape_runs(shape, slide_idx, shape.shape_id, hint)
        segments.extend(segs)


def _extract_comments(prs) -> list[TextSegment]:
    segments = []
    from pptx.oxml.ns import qn
    for slide_idx, slide in enumerate(prs.slides):
        try:
            cmt_part = slide.part.part_related_by(CMT_REL_TYPE)
        except KeyError:
            continue
        for cmt in cmt_part.element.iterchildren(qn("p:cmt")):
            cmt_text_el = cmt.find(qn("p:cmtText"))
            if cmt_text_el is not None:
                text = _get_text(cmt_text_el).strip()
                if text and _should_translate(text):
                    segments.append(TextSegment(
                        id=f"s{slide_idx}_comment_{len(segments)}",
                        slide_idx=slide_idx,
                        shape_id=-1,
                        para_idx=0,
                        run_idx=0,
                        original_text=text,
                        element_type=ElementType.COMMENT_TEXT,
                        location_hint=["comment"],
                    ))
    return segments


def _get_text(element):
    from pptx.oxml.ns import qn
    a_texts = [t.text or "" for t in element.iter(qn("a:t"))]
    if a_texts:
        return "".join(a_texts)
    p_texts = [t.text or "" for t in element.iter(qn("p:t"))]
    return "".join(p_texts)


def _should_translate(text: str) -> bool:
    import re
    s = text.strip()
    if not s:
        return False
    if re.match(r'^[\d\s\-–—.,;:!?/\\()\[\]{}<>""''\u00ab\u00bb\u00b7\u2022\u25cf\u25a0\u25b2\u25bc\u25b6\u25c0\u25cb\u2605\u2606\u2666\u25c6\u25d8\u2713\u2717\u2718+=*^%$#@&~`|\u00a0\u2000-\u200f\u2028-\u202f]+$', s):
        return False
    return True
