"""Paragraph-level extraction: merge runs into paragraphs while keeping
per-run metadata (whitespace, word count, formatting) for later splitting."""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from ..models.paragraph_segment import ParagraphSegment, RunInfo
from ..models.segment import ElementType
from ..utils.text import should_translate, snapshot_font

CMT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


def extract_paragraphs(pptx_path: str, logger=None) -> list[ParagraphSegment]:
    prs = Presentation(str(pptx_path))
    segments: list[ParagraphSegment] = []
    _ID_COUNTER[0] = 0

    for slide_idx, slide in enumerate(prs.slides):
        if logger:
            logger.debug(f"  Slide {slide_idx + 1}/{len(prs.slides)}")
        for shape in slide.shapes:
            _extract_shape(shape, slide_idx, segments, [])
        segments.extend(_extract_notes(slide, slide_idx))

    segments.extend(_extract_comments(prs))

    if logger:
        logger.info(f"Extracted {len(segments)} paragraph segments")
    return segments


_ID_COUNTER = [0]


def _next_id(slide_idx: int, shape_id: int, para_idx: int) -> str:
    _ID_COUNTER[0] += 1
    return f"s{slide_idx}_sh{shape_id}_p{para_idx}_seg{_ID_COUNTER[0]}"


# ── dispatch ──────────────────────────────────────────────────────────────

def _extract_shape(shape, slide_idx: int, segments: list, hint: list):
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        _extract_group(shape, slide_idx, segments, hint)
    elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
        _extract_table(shape, slide_idx, segments, hint)
    elif shape.shape_type == MSO_SHAPE_TYPE.CHART:
        _extract_chart(shape, slide_idx, segments, hint)
    elif shape.shape_type == MSO_SHAPE_TYPE.DIAGRAM:
        segments.append(_smartart_placeholder(shape, slide_idx, hint))
    elif shape.has_text_frame:
        _extract_text_frame(
            shape.text_frame, shape.shape_id, slide_idx, segments, hint,
            ElementType.PARAGRAPH,
        )


def _extract_group(group, slide_idx: int, segments: list, hint: list):
    hint = hint + [f"group_{group.shape_id}"]
    try:
        sub_shapes = group.shapes
    except Exception:
        return
    for sub in sub_shapes:
        _extract_shape(sub, slide_idx, segments, hint)


def _extract_table(shape, slide_idx: int, segments: list, hint: list):
    table = shape.table
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            tf = cell.text_frame
            if tf is None:
                continue
            cell_hint = hint + ["table", row_idx, col_idx]
            _extract_text_frame(tf, shape.shape_id, slide_idx, segments, cell_hint,
                                ElementType.TABLE_CELL)


def _extract_chart(shape, slide_idx: int, segments: list, hint: list):
    try:
        chart = shape.chart
    except Exception:
        return
    try:
        if chart.chart_title and chart.chart_title.has_text_frame:
            _extract_text_frame(chart.chart_title.text_frame, shape.shape_id,
                                slide_idx, segments, hint + ["chart_title"],
                                ElementType.CHART_TITLE)
    except Exception:
        pass
    for axis_name, axis in [("category", getattr(chart, "category_axis", None)),
                            ("value", getattr(chart, "value_axis", None))]:
        if axis is None:
            continue
        try:
            at = axis.axis_title
            if at and at.has_text_frame:
                _extract_text_frame(at.text_frame, shape.shape_id, slide_idx,
                                    segments, hint + [f"{axis_name}_axis_title"],
                                    ElementType.AXIS_TITLE)
        except Exception:
            pass


def _extract_notes(slide, slide_idx: int) -> list[ParagraphSegment]:
    segments = []
    if not slide.has_notes_slide:
        return segments
    for shape in slide.notes_slide.shapes:
        if shape.has_text_frame:
            _extract_text_frame(shape.text_frame, shape.shape_id, slide_idx,
                                segments, ["notes"], ElementType.NOTE)
    return segments


# ── core paragraph builder ────────────────────────────────────────────────

def _extract_text_frame(tf, shape_id: int, slide_idx: int, segments: list,
                        hint: list, element_type: ElementType):
    for para_idx, para in enumerate(tf.paragraphs):
        seg = _build_segment(para, para_idx, slide_idx, shape_id, hint, element_type)
        if seg is not None:
            segments.append(seg)


def _build_segment(para, para_idx: int, slide_idx: int, shape_id: int,
                   hint: list, element_type: ElementType):
    runs_meta: list[RunInfo] = []
    parts: list[str] = []
    for run_idx, run in enumerate(para.runs):
        original = run.text
        stripped = original.strip()
        leading = original[:len(original) - len(original.lstrip())]
        trailing = original[len(original.rstrip()):]
        runs_meta.append(RunInfo(
            run_idx=run_idx,
            text=original,
            leading_ws=leading,
            trailing_ws=trailing,
            char_len=len(original),
            word_count=len(stripped.split()) if stripped else 0,
            formatting=snapshot_font(run),
        ))
        parts.append(original)

    full_text = "".join(parts)
    if not should_translate(full_text):
        return None

    return ParagraphSegment(
        id=_next_id(slide_idx, shape_id, para_idx),
        slide_idx=slide_idx,
        shape_id=shape_id,
        para_idx=para_idx,
        full_text=full_text,
        element_type=element_type,
        runs=runs_meta,
        location_hint=list(hint),
    )


def _smartart_placeholder(shape, slide_idx: int, hint: list) -> ParagraphSegment:
    return ParagraphSegment(
        id=f"s{slide_idx}_sh{shape.shape_id}_smartart",
        slide_idx=slide_idx,
        shape_id=shape.shape_id,
        para_idx=0,
        full_text="",
        element_type=ElementType.SMARTART_PLACEHOLDER,
        location_hint=list(hint) + ["smartart"],
        skip=True,
    )


def _extract_comments(prs) -> list[ParagraphSegment]:
    from pptx.oxml.ns import qn
    segments = []
    for slide_idx, slide in enumerate(prs.slides):
        try:
            cmt_part = slide.part.part_related_by(CMT_REL_TYPE)
        except KeyError:
            continue
        for cmt in cmt_part.element.iterchildren(qn("p:cmt")):
            cmt_text_el = cmt.find(qn("p:cmtText"))
            if cmt_text_el is None:
                continue
            text = _get_text(cmt_text_el).strip()
            if should_translate(text):
                segments.append(ParagraphSegment(
                    id=f"s{slide_idx}_comment_{len(segments)}",
                    slide_idx=slide_idx,
                    shape_id=-1,
                    para_idx=0,
                    full_text=text,
                    element_type=ElementType.COMMENT_TEXT,
                    location_hint=["comment"],
                ))
    return segments


def _get_text(element) -> str:
    from pptx.oxml.ns import qn
    a_texts = [t.text or "" for t in element.iter(qn("a:t"))]
    if a_texts:
        return "".join(a_texts)
    p_texts = [t.text or "" for t in element.iter(qn("p:t"))]
    return "".join(p_texts)
