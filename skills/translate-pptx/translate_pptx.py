#!/usr/bin/env python3
"""translate_pptx.py — Extract & apply translations for .pptx files.

Usage:
    python translate_pptx.py extract <input.pptx> <output.json>
    python translate_pptx.py apply  <input.pptx> <translations.json>
"""

import json
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn

CMT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"


def get_text(element):
    a_texts = [t.text or "" for t in element.iter(qn("a:t"))]
    if a_texts:
        return "".join(a_texts)
    p_texts = [t.text or "" for t in element.iter(qn("p:t"))]
    return "".join(p_texts)


def set_text(element, text):
    t_els = list(element.iter(qn("a:t")))
    if not t_els:
        t_els = list(element.iter(qn("p:t")))
    if t_els:
        t_els[0].text = text
        for t in t_els[1:]:
            t.text = None


def should_translate(text):
    s = text.strip()
    if not s:
        return False
    if re.match(
        r'^[\d\s\-–—.,;:!?/\\()\[\]{}<>""''\u00ab\u00bb\u00b7\u2022\u25cf\u25a0\u25b2\u25bc\u25b6\u25c0\u25cb\u2605\u2606\u2666\u25c6\u25d8\u2713\u2717\u2718+=*^%$#@&~`|\u00a0\u2000-\u200f\u2028-\u202f]+$',
        s,
    ):
        return False
    return True


def traverse_chart(shape):
    try:
        chart = shape.chart
    except Exception:
        return

    try:
        if chart.chart_title.has_text_frame:
            for p in chart.chart_title._element.iter(qn("a:p")):
                text = get_text(p)
                if should_translate(text):
                    yield p, text.strip(), "chart_text"
    except Exception:
        pass

    try:
        cat = chart.category_axis
        if cat.axis_title.has_text_frame:
            for p in cat.axis_title._element.iter(qn("a:p")):
                text = get_text(p)
                if should_translate(text):
                    yield p, text.strip(), "chart_text"
    except Exception:
        pass

    try:
        val = chart.value_axis
        if val.axis_title.has_text_frame:
            for p in val.axis_title._element.iter(qn("a:p")):
                text = get_text(p)
                if should_translate(text):
                    yield p, text.strip(), "chart_text"
    except Exception:
        pass


def traverse_slide_shapes(shapes, default_type="paragraph"):
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from traverse_slide_shapes(shape.shapes, default_type)
        elif shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if should_translate(text):
                        txBody = cell._tc.find(qn("a:txBody"))
                        if txBody is not None:
                            yield txBody, text, "table_cell"
                        else:
                            yield cell._tc, text, "table_cell"
        elif shape.has_chart:
            yield from traverse_chart(shape)
        elif shape.has_text_frame:
            txBody = shape._element.find(qn("p:txBody"))
            if txBody is not None:
                for p in txBody.iterchildren(qn("a:p")):
                    text = get_text(p)
                    if should_translate(text):
                        yield p, text.strip(), default_type


def traverse_slide_notes(slide):
    if not slide.has_notes_slide:
        return
    notes_slide = slide.notes_slide
    for shape in notes_slide.shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            for element, text, _ in traverse_slide_shapes(shape.shapes, "notes"):
                yield element, text, "notes"
        elif shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if should_translate(text):
                        txBody = cell._tc.find(qn("a:txBody"))
                        if txBody is not None:
                            yield txBody, text, "notes"
                        else:
                            yield cell._tc, text, "notes"
        elif shape.has_text_frame:
            txBody = shape._element.find(qn("p:txBody"))
            if txBody is not None:
                for p in txBody.iterchildren(qn("a:p")):
                    text = get_text(p)
                    if should_translate(text):
                        yield p, text.strip(), "notes"


def traverse_comments(prs):
    for slide in prs.slides:
        try:
            cmt_part = slide.part.part_related_by(CMT_REL_TYPE)
        except KeyError:
            continue
        for cmt in cmt_part.element.iterchildren(qn("p:cmt")):
            cmt_text_el = cmt.find(qn("p:cmtText"))
            if cmt_text_el is not None:
                text = get_text(cmt_text_el)
                if should_translate(text):
                    yield cmt_text_el, text.strip(), "comment"


def traverse(prs):
    for slide in prs.slides:
        yield from traverse_slide_shapes(slide.shapes)
        yield from traverse_slide_notes(slide)
    yield from traverse_comments(prs)


def extract(pptx_path, json_path):
    prs = Presentation(str(pptx_path))
    segments = []
    for _element, text, seg_type in traverse(prs):
        segments.append(
            {
                "id": len(segments),
                "type": seg_type,
                "text": text,
            }
        )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    print(f"Extracted {len(segments)} segments to {json_path}")
    return segments


def apply(pptx_path, json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    prs = Presentation(str(pptx_path))

    for i, (element, _text, _seg_type) in enumerate(traverse(prs)):
        if i >= len(segments):
            break
        translated = segments[i].get("translated_text")
        if translated and translated != segments[i].get("text"):
            set_text(element, translated)

    out_path = pptx_path.parent / f"{pptx_path.stem}.en.pptx"
    prs.save(str(out_path))
    print(f"Saved translated presentation to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python translate_pptx.py extract <input.pptx> <output.json>")
        print("  python translate_pptx.py apply  <input.pptx> <translations.json>")
        sys.exit(1)

    mode = sys.argv[1]
    pptx_path = Path(sys.argv[2])
    json_path = Path(sys.argv[3])

    if mode == "extract":
        extract(pptx_path, json_path)
    elif mode == "apply":
        apply(pptx_path, json_path)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
