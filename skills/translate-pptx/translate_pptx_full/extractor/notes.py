from ..models.segment import TextSegment, FontSnapshot, ElementType


def extract_notes_runs(slide, slide_idx: int) -> list[TextSegment]:
    segments = []
    if not slide.has_notes_slide:
        return segments
    notes_slide = slide.notes_slide
    for shape in notes_slide.shapes:
        if not shape.has_text_frame:
            continue
        tf = shape.text_frame
        if tf is None:
            continue
        for para_idx, para in enumerate(tf.paragraphs):
            for run_idx, run in enumerate(para.runs):
                original = run.text
                stripped = original.strip()
                if not stripped or not _should_translate(stripped):
                    continue
                leading = original[:len(original) - len(original.lstrip())]
                trailing = original[len(original.rstrip()):]
                fmt = _snapshot_run_font(run)
                segments.append(TextSegment(
                    id=f"s{slide_idx}_notes_p{para_idx}_r{run_idx}",
                    slide_idx=slide_idx,
                    shape_id=shape.shape_id,
                    para_idx=para_idx,
                    run_idx=run_idx,
                    original_text=stripped,
                    element_type=ElementType.NOTE_RUN,
                    location_hint=["notes"],
                    formatting=fmt,
                    leading_ws=leading,
                    trailing_ws=trailing,
                ))
    return segments


def _snapshot_run_font(run) -> FontSnapshot:
    f = run.font
    color = None
    try:
        if f.color and f.color.rgb:
            color = str(f.color.rgb)
    except AttributeError:
        pass
    return FontSnapshot(
        bold=f.bold,
        italic=f.italic,
        underline=f.underline,
        size_pt=f.size.pt if f.size else None,
        color_rgb=color,
        name=f.name,
    )


def _should_translate(text: str) -> bool:
    import re
    s = text.strip()
    if not s:
        return False
    if re.match(r'^[\d\s\-–—.,;:!?/\\()\[\]{}<>""''\u00ab\u00bb\u00b7\u2022\u25cf\u25a0\u25b2\u25bc\u25b6\u25c0\u25cb\u2605\u2606\u2666\u25c6\u25d8\u2713\u2717\u2718+=*^%$#@&~`|\u00a0\u2000-\u200f\u2028-\u202f]+$', s):
        return False
    return True
