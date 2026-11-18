from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from ..models.segment import TextSegment, ElementType
from ..models.manifest import TranslationManifest
from ..utils.logging import get_logger, ProgressBar


def apply_all(manifest: TranslationManifest, output_path: str, logger=None):
    prs = Presentation(str(manifest.source_path))
    segments = manifest.segments
    total = len(segments)

    if logger:
        logger.info(f"Applying {total} translations to {output_path}")

    bar = ProgressBar(total, "Apply")
    for seg in segments:
        if seg.skip:
            bar.update(1)
            continue
        if not seg.translated_text or seg.translated_text == seg.original_text:
            bar.update(1)
            continue
        _apply_segment(prs, seg, logger)
        bar.update(1)

    bar.close()
    prs.save(str(output_path))
    if logger:
        logger.info(f"Saved translated presentation to {output_path}")


CMT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


def _apply_segment(prs, seg: TextSegment, logger=None):
    if seg.element_type == ElementType.COMMENT_TEXT:
        _apply_comment(prs, seg, logger)
        return

    if seg.element_type == ElementType.NOTE_RUN:
        _apply_note_run(prs, seg, logger)
        return

    if seg.element_type == ElementType.CHART_TITLE_RUN:
        _apply_chart_title_run(prs, seg, logger)
        return

    if seg.element_type == ElementType.AXIS_TITLE_RUN:
        _apply_axis_title_run(prs, seg, logger)
        return

    if seg.element_type == ElementType.TABLE_CELL_RUN:
        _apply_table_cell_run(prs, seg, logger)
        return

    _apply_shape_run(prs, seg, logger)


def _apply_shape_run(prs, seg: TextSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]
        shape = _find_shape_by_id(slide, seg.shape_id)
        if shape is None:
            if logger:
                logger.warning(f"  Shape {seg.shape_id} not found on slide {seg.slide_idx}")
            return
        if not shape.has_text_frame:
            return
        tf = shape.text_frame
        if seg.para_idx >= len(tf.paragraphs):
            return
        para = tf.paragraphs[seg.para_idx]
        if seg.run_idx >= len(para.runs):
            return
        para.runs[seg.run_idx].text = seg.leading_ws + (seg.translated_text or "") + seg.trailing_ws
    except Exception as e:
        if logger:
            logger.warning(f"  Failed to apply segment {seg.id}: {e}")


def _apply_note_run(prs, seg: TextSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]
        if not slide.has_notes_slide:
            return
        ns = slide.notes_slide
        for shape in ns.shapes:
            if not shape.has_text_frame:
                continue
            tf = shape.text_frame
            if seg.para_idx < len(tf.paragraphs):
                para = tf.paragraphs[seg.para_idx]
                if seg.run_idx < len(para.runs):
                    para.runs[seg.run_idx].text = seg.leading_ws + (seg.translated_text or "") + seg.trailing_ws
                    return
    except Exception as e:
        if logger:
            logger.warning(f"  Failed to apply note segment {seg.id}: {e}")


def _apply_chart_title_run(prs, seg: TextSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]
        shape = _find_shape_by_id(slide, seg.shape_id)
        if shape is None or not shape.has_chart:
            return
        chart = shape.chart
        if not chart.chart_title or not chart.chart_title.has_text_frame:
            return
        tf = chart.chart_title.text_frame
        if seg.para_idx < len(tf.paragraphs):
            para = tf.paragraphs[seg.para_idx]
            if seg.run_idx < len(para.runs):
                para.runs[seg.run_idx].text = seg.leading_ws + (seg.translated_text or "") + seg.trailing_ws
    except Exception as e:
        if logger:
            logger.warning(f"  Failed to apply chart title {seg.id}: {e}")


def _apply_axis_title_run(prs, seg: TextSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]
        shape = _find_shape_by_id(slide, seg.shape_id)
        if shape is None or not shape.has_chart:
            return
        chart = shape.chart
        for axis in [chart.category_axis, chart.value_axis]:
            if axis is None:
                continue
            at = axis.axis_title
            if at and at.has_text_frame:
                tf = at.text_frame
                if seg.para_idx < len(tf.paragraphs):
                    para = tf.paragraphs[seg.para_idx]
                    if seg.run_idx < len(para.runs):
                        para.runs[seg.run_idx].text = seg.leading_ws + (seg.translated_text or "") + seg.trailing_ws
                        return
    except Exception as e:
        if logger:
            logger.warning(f"  Failed to apply axis title {seg.id}: {e}")


def _apply_table_cell_run(prs, seg: TextSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]
        shape = _find_shape_by_id(slide, seg.shape_id)
        if shape is None or not shape.has_table:
            if logger:
                logger.warning(f"  Table shape {seg.shape_id} not found on slide {seg.slide_idx}")
            return
        table = shape.table
        row_idx = None
        col_idx = None
        for hint in seg.location_hint:
            if hint == "table":
                continue
            if isinstance(hint, int):
                if row_idx is None:
                    row_idx = hint
                else:
                    col_idx = hint
        if row_idx is None or col_idx is None:
            if seg.location_hint and len(seg.location_hint) >= 3:
                row_idx = seg.location_hint[-2]
                col_idx = seg.location_hint[-1]
        if row_idx is None or col_idx is None:
            return
        if row_idx >= len(table.rows) or col_idx >= len(table.columns):
            return
        cell = table.cell(row_idx, col_idx)
        tf = cell.text_frame
        if seg.para_idx < len(tf.paragraphs):
            para = tf.paragraphs[seg.para_idx]
            if seg.run_idx < len(para.runs):
                para.runs[seg.run_idx].text = seg.leading_ws + (seg.translated_text or "") + seg.trailing_ws
    except Exception as e:
        if logger:
            logger.warning(f"  Failed to apply table cell {seg.id}: {e}")


def _apply_comment(prs, seg: TextSegment, logger=None):
    from pptx.oxml.ns import qn
    try:
        slide = prs.slides[seg.slide_idx]
        cmt_part = slide.part.part_related_by(CMT_REL_TYPE)
    except (KeyError, Exception):
        return
    cmt_elements = list(cmt_part.element.iterchildren(qn("p:cmt")))
    cmt_idx = int(seg.id.split("_")[-1]) if "_" in seg.id else 0
    if cmt_idx < len(cmt_elements):
        cmt_text_el = cmt_elements[cmt_idx].find(qn("p:cmtText"))
        if cmt_text_el is not None:
            t_els = list(cmt_text_el.iter(qn("a:t")))
            if t_els:
                t_els[0].text = seg.leading_ws + (seg.translated_text or "") + seg.trailing_ws
                for t in t_els[1:]:
                    t.text = None


def _find_shape_by_id(slide, target_id: int):
    for shape in slide.shapes:
        if shape.shape_id == target_id:
            return shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            found = _find_in_group(shape, target_id)
            if found:
                return found
    return None


def _find_in_group(group_shape, target_id: int):
    try:
        for shape in group_shape.shapes:
            if shape.shape_id == target_id:
                return shape
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                found = _find_in_group(shape, target_id)
                if found:
                    return found
    except Exception:
        pass
    return None
