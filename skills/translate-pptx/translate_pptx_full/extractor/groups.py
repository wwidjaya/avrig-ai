from pptx.enum.shapes import MSO_SHAPE_TYPE

from ..models.segment import TextSegment, FontSnapshot, ElementType
from .shapes import extract_shape_runs
from .tables import extract_table_runs
from .charts import extract_chart_runs


def extract_group_runs(group_shape, slide_idx: int, location_hint: list = None) -> list[TextSegment]:
    segments = []
    hint = list(location_hint) if location_hint else []
    hint.append(f"group_{group_shape.shape_id}")

    try:
        sub_shapes = group_shape.shapes
    except Exception:
        return segments

    for sub_shape in sub_shapes:
        if sub_shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            sub_segs = extract_group_runs(sub_shape, slide_idx, hint)
            segments.extend(sub_segs)
        elif sub_shape.shape_type == MSO_SHAPE_TYPE.TABLE:
            sub_segs = extract_table_runs(sub_shape, slide_idx, sub_shape.shape_id, hint)
            segments.extend(sub_segs)
        elif sub_shape.shape_type == MSO_SHAPE_TYPE.CHART:
            sub_segs = extract_chart_runs(sub_shape, slide_idx, sub_shape.shape_id, hint)
            segments.extend(sub_segs)
        elif sub_shape.has_text_frame:
            sub_segs = extract_shape_runs(sub_shape, slide_idx, sub_shape.shape_id, hint)
            segments.extend(sub_segs)

    return segments
