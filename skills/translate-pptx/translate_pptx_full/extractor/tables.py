from ..models.segment import TextSegment, FontSnapshot, ElementType


def extract_table_runs(shape, slide_idx: int, shape_id: int, location_hint: list = None) -> list[TextSegment]:
    segments = []
    hint = list(location_hint) if location_hint else []
    table = shape.table
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            tf = cell.text_frame
            if not tf:
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
                        id=f"s{slide_idx}_sh{shape_id}_t{row_idx}_{col_idx}_p{para_idx}_r{run_idx}",
                        slide_idx=slide_idx,
                        shape_id=shape_id,
                        para_idx=para_idx,
                        run_idx=run_idx,
                        original_text=stripped,
                        element_type=ElementType.TABLE_CELL_RUN,
                        location_hint=hint + ["table", row_idx, col_idx],
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
