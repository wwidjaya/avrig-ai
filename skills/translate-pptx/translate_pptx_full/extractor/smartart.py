from ..models.segment import TextSegment, ElementType


def extract_smartart(shape, slide_idx: int, shape_id: int, location_hint: list = None) -> list[TextSegment]:
    hint = list(location_hint) if location_hint else []
    hint.append("smartart")
    segments = []

    try:
        from pptx.oxml.ns import qn
        el = shape._element
        dgm_ts = el.iter(qn("dgm:t"))
        texts = []
        for t in dgm_ts:
            if t.text and t.text.strip():
                texts.append(t.text.strip())
        if texts:
            combined = " | ".join(texts)
            segments.append(TextSegment(
                id=f"s{slide_idx}_sh{shape_id}_smartart",
                slide_idx=slide_idx,
                shape_id=shape_id,
                para_idx=0,
                run_idx=0,
                original_text=combined,
                element_type=ElementType.SMARTART_PLACEHOLDER,
                location_hint=hint,
                skip=True,
            ))
            return segments
    except Exception:
        pass

    segments.append(TextSegment(
        id=f"s{slide_idx}_sh{shape_id}_smartart_unreadable",
        slide_idx=slide_idx,
        shape_id=shape_id,
        para_idx=0,
        run_idx=0,
        original_text="",
        element_type=ElementType.SMARTART_PLACEHOLDER,
        location_hint=hint,
        skip=True,
    ))
    return segments
