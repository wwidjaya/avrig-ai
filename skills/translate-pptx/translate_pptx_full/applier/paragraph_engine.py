"""Paragraph-level apply.

Two paths, tried in order for each paragraph:
  1. Align path    — deterministic semantic alignment: each translated word
     is matched back to the source word it came from (cognate similarity +
     max-weight assignment), so the font style follows the ORIGINAL word
     even when the translation reorders words.
  2. Positional    — split translated text proportionally across original runs.
"""

import copy

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn

from ..models.paragraph_segment import ParagraphSegment
from ..models.segment import ElementType
from ..splitter import split_translation_by_runs
from ..aligner import align_segment
from ..utils.logging import ProgressBar

CMT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


def apply_paragraphs(manifest, output_path: str, config=None, logger=None):
    prs = Presentation(str(manifest.source_path))
    segments = manifest.segments
    total = len(segments)

    if logger:
        logger.info(f"Applying {total} paragraph translations to {output_path}")

    bar = ProgressBar(total, "Apply")
    for seg in segments:
        if seg.skip:
            bar.update(1)
            continue
        if not seg.translated_text or seg.translated_text.strip() == seg.full_text.strip():
            bar.update(1)
            continue
        _apply_segment(prs, seg, config, logger)
        bar.update(1)

    bar.close()
    prs.save(str(output_path))
    if logger:
        logger.info(f"Saved translated presentation to {output_path}")


def _apply_segment(prs, seg: ParagraphSegment, config=None, logger=None):
    if seg.element_type == ElementType.COMMENT_TEXT:
        _apply_comment(prs, seg, logger)
        return

    para = _locate_paragraph(prs, seg, logger)
    if para is None:
        return

    translated = seg.translated_text or seg.full_text

    # Path 0: single content run — whole paragraph shares one style;
    # apply translation directly to that run.
    content_runs = [r for r in seg.runs if r.word_count > 0]
    if len(content_runs) == 1:
        _apply_single_style(para, seg, content_runs[0], translated)
        return

    # Path 1: deterministic alignment (style follows original word)
    if config is not None:
        result = align_segment(seg, translated, config, logger)
        if result is not None:
            if _rebuild_aligned(para, seg, translated, result.run_indices):
                return

    # Path 2: positional proportional split (fallback)
    per_run_texts = split_translation_by_runs(seg.runs, translated)
    for run_info, new_text in zip(seg.runs, per_run_texts):
        if run_info.run_idx < len(para.runs):
            para.runs[run_info.run_idx].text = new_text


def _apply_single_style(para, seg: ParagraphSegment, content_run, translated: str):
    """Whole paragraph has one style: put the translation in that run,
    clear the rest."""
    rpr_by_run = _capture_rpr(para, seg)
    for r_el in para._p.findall(qn("a:r")):
        para._p.remove(r_el)
    run = para.add_run()
    run.text = translated
    r_el = run._r
    existing = r_el.find(qn("a:rPr"))
    if existing is not None:
        r_el.remove(existing)
    rpr = rpr_by_run.get(content_run.run_idx)
    if rpr is not None:
        r_el.insert(0, copy.deepcopy(rpr))


# ── Path 1: rebuild from aligned run indices ─────────────────────────────

def _rebuild_aligned(para, seg: ParagraphSegment, translated: str, run_indices) -> bool:
    words = translated.split()
    if len(words) != len(run_indices):
        return False
    rpr_by_run = _capture_rpr(para, seg)

    # group consecutive words sharing a run index into single spans
    spans = []
    for word, ridx in zip(words, run_indices):
        if spans and spans[-1][1] == ridx:
            spans[-1] = (spans[-1][0] + " " + word, ridx)
        else:
            spans.append((word, ridx))
    _rebuild_runs(para, seg, spans, rpr_by_run)
    return True


# ── shared helpers ────────────────────────────────────────────────────────

def _capture_rpr(para, seg: ParagraphSegment) -> dict:
    """Deep-copy each source run's rPr XML keyed by run_idx, so we can
    restore the exact formatting (font, size, color, bold, italic...) after
    rebuilding the run sequence."""
    rpr_by_run = {}
    for run, run_info in zip(para.runs, seg.runs):
        rpr_el = run._r.find(qn("a:rPr"))
        rpr_by_run[run_info.run_idx] = copy.deepcopy(rpr_el) if rpr_el is not None else None
    return rpr_by_run


def _rebuild_runs(para, seg: ParagraphSegment, spans, rpr_by_run: dict):
    """Remove existing runs and create new ones in translated order,
    restoring each span's rPr from its source run. A single space is
    inserted between spans when neither side already carries whitespace
    (models often trim spaces when moving markers)."""
    for r_el in para._p.findall(qn("a:r")):
        para._p.remove(r_el)

    prev_text = ""
    for text, ridx in spans:
        if (
            prev_text
            and not prev_text.endswith((" ", "\u00a0", "\x0b", "\n"))
            and not text.startswith((" ", "\u00a0", "\x0b", "\n"))
        ):
            text = " " + text
        run = para.add_run()
        run.text = text
        r_el = run._r
        existing = r_el.find(qn("a:rPr"))
        if existing is not None:
            r_el.remove(existing)
        rpr = rpr_by_run.get(ridx)
        if rpr is not None:
            r_el.insert(0, copy.deepcopy(rpr))
        prev_text = text


# ── navigation ────────────────────────────────────────────────────────────

def _locate_paragraph(prs, seg: ParagraphSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]

        if seg.element_type == ElementType.NOTE:
            return _find_note_paragraph(slide, seg)

        shape = _find_shape_by_id(slide, seg.shape_id)
        if shape is None:
            if logger:
                logger.warning(f"  Shape {seg.shape_id} not found on slide {seg.slide_idx}")
            return None

        if seg.element_type == ElementType.TABLE_CELL:
            tf = _find_cell_text_frame(shape, seg)
            if tf is None:
                return None
        elif seg.element_type == ElementType.CHART_TITLE:
            tf = _find_chart_title_text_frame(shape, seg)
            if tf is None:
                return None
        elif seg.element_type == ElementType.AXIS_TITLE:
            tf = _find_axis_title_text_frame(shape, seg)
            if tf is None:
                return None
        elif shape.has_text_frame:
            tf = shape.text_frame
        else:
            return None

        if seg.para_idx < len(tf.paragraphs):
            return tf.paragraphs[seg.para_idx]
    except Exception as e:
        if logger:
            logger.warning(f"  Failed to locate paragraph {seg.id}: {e}")
    return None


def _find_note_paragraph(slide, seg: ParagraphSegment):
    if not slide.has_notes_slide:
        return None
    for shape in slide.notes_slide.shapes:
        if not shape.has_text_frame:
            continue
        # Match by shape_id captured at extraction time; fall back to
        # any shape whose paragraph index fits and has runs.
        if seg.shape_id != -1 and shape.shape_id == seg.shape_id:
            tf = shape.text_frame
            if seg.para_idx < len(tf.paragraphs):
                return tf.paragraphs[seg.para_idx]
    for shape in slide.notes_slide.shapes:
        if not shape.has_text_frame:
            continue
        tf = shape.text_frame
        if seg.para_idx < len(tf.paragraphs) and len(tf.paragraphs[seg.para_idx].runs) > 0:
            return tf.paragraphs[seg.para_idx]
    return None


def _find_cell_text_frame(shape, seg: ParagraphSegment):
    if not shape.has_table:
        return None
    table = shape.table
    row_idx = col_idx = None
    for hint in seg.location_hint:
        if isinstance(hint, int):
            if row_idx is None:
                row_idx = hint
            else:
                col_idx = hint
    if row_idx is None or col_idx is None:
        return None
    if row_idx >= len(table.rows) or col_idx >= len(table.columns):
        return None
    return table.cell(row_idx, col_idx).text_frame


def _find_chart_title_text_frame(shape, seg: ParagraphSegment):
    if not shape.has_chart:
        return None
    try:
        chart = shape.chart
        if chart.chart_title and chart.chart_title.has_text_frame:
            return chart.chart_title.text_frame
    except Exception:
        pass
    return None


def _find_axis_title_text_frame(shape, seg: ParagraphSegment):
    if not shape.has_chart:
        return None
    try:
        chart = shape.chart
        for axis in [chart.category_axis, chart.value_axis]:
            if axis is None:
                continue
            at = axis.axis_title
            if at and at.has_text_frame:
                return at.text_frame
    except Exception:
        pass
    return None


def _apply_comment(prs, seg: ParagraphSegment, logger=None):
    try:
        slide = prs.slides[seg.slide_idx]
        cmt_part = slide.part.part_related_by(CMT_REL_TYPE)
    except (KeyError, Exception):
        return
    from pptx.oxml.ns import qn
    cmt_elements = list(cmt_part.element.iterchildren(qn("p:cmt")))
    cmt_idx = int(seg.id.split("_")[-1]) if "_" in seg.id else 0
    if cmt_idx < len(cmt_elements):
        cmt_text_el = cmt_elements[cmt_idx].find(qn("p:cmtText"))
        if cmt_text_el is not None:
            t_els = list(cmt_text_el.iter(qn("a:t")))
            if t_els:
                t_els[0].text = seg.translated_text
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
