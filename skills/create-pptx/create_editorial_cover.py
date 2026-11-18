#!/usr/bin/env python3
"""Create an editable editorial cover by making surgical OOXML edits.

The script preserves the original PowerPoint XML and package extensions. It
repositions the cover photo and text, crops the photo to a right-side frame,
sets a white canvas, and removes an existing overlay. No python-pptx dependency.
"""
import argparse
import html
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def match_fragment(data: bytes, tag: bytes, shape_id: str) -> tuple[re.Match[bytes], bytes]:
    pat = re.compile(rb"<" + tag + rb"\b.*?</" + tag + rb">", re.S)
    for m in pat.finditer(data):
        if re.search(rb'<p:cNvPr\b[^>]*\bid="' + re.escape(shape_id.encode()) + rb'"', m.group()):
            return m, m.group()
    raise ValueError(f"Could not find {tag.decode()} object with id {shape_id}")


def set_xfrm(fragment: bytes, x: int, y: int, cx: int, cy: int) -> bytes:
    m = re.search(rb"<a:xfrm\b[^>]*>.*?</a:xfrm>", fragment, re.S)
    if not m:
        raise ValueError("Object has no editable transform")
    xf = m.group()
    for tag, attrs in ((b"off", {b"x": x, b"y": y}), (b"ext", {b"cx": cx, b"cy": cy})):
        obj = re.search(rb"<a:" + tag + rb"\b[^>]*/>", xf)
        if not obj:
            raise ValueError("Object transform is incomplete")
        val = obj.group()
        for key, number in attrs.items():
            val, count = re.subn(rb"\b" + key + rb'="[^"]*"', key + b'="' + str(number).encode() + b'"', val, count=1)
            if not count:
                val = val[:-2] + b" " + key + b'="' + str(number).encode() + b'"/>'
        xf = xf[:obj.start()] + val + xf[obj.end():]
    return fragment[:m.start()] + xf + fragment[m.end():]


def replace_text(fragment: bytes, values: list[str]) -> bytes:
    paras = list(re.finditer(rb"<a:p\b.*?</a:p>", fragment, re.S))
    if len(paras) < len(values):
        raise ValueError("Text box has fewer paragraphs than the requested values")
    for index, value in enumerate(values):
        para = paras[index].group()
        nodes = list(re.finditer(rb"<a:t(?:\s[^>]*)?>.*?</a:t>", para, re.S))
        if not nodes:
            raise ValueError(f"Text paragraph {index + 1} has no editable text run")
        for node_index, node in reversed(list(enumerate(nodes))):
            raw = ("<a:t>" + html.escape(value, quote=False) + "</a:t>").encode() if node_index == 0 else b"<a:t></a:t>"
            para = para[:node.start()] + raw + para[node.end():]
        fragment = fragment[:paras[index].start()] + para + fragment[paras[index].end():]
        # Earlier substitutions may change byte offsets; refresh paragraph matches.
        paras = list(re.finditer(rb"<a:p\b.*?</a:p>", fragment, re.S))
    return fragment


def replace_paragraph(fragment: bytes, index: int, value: str) -> bytes:
    paras = list(re.finditer(rb"<a:p\b.*?</a:p>", fragment, re.S))
    if index >= len(paras):
        raise ValueError(f"Text box has no paragraph {index + 1}")
    para = paras[index].group()
    nodes = list(re.finditer(rb"<a:t(?:\s[^>]*)?>.*?</a:t>", para, re.S))
    if not nodes:
        raise ValueError(f"Text paragraph {index + 1} has no editable text run")
    for node_index, node in reversed(list(enumerate(nodes))):
        raw = ("<a:t>" + html.escape(value, quote=False) + "</a:t>").encode() if node_index == 0 else b"<a:t></a:t>"
        para = para[:node.start()] + raw + para[node.end():]
    return fragment[:paras[index].start()] + para + fragment[paras[index].end():]


def style_text(fragment: bytes, color: str, sizes: list[int]) -> bytes:
    paras = list(re.finditer(rb"<a:p\b.*?</a:p>", fragment, re.S))
    for i in reversed(range(len(paras))):
        size = sizes[min(i, len(sizes) - 1)]
        para = paras[i].group()

        def style_prop(m: re.Match[bytes]) -> bytes:
            tag, attrs = m.group(1), m.group(2)
            attrs = re.sub(rb'\bsz="[^"]*"', b"", attrs)
            attrs = attrs.rstrip() + b' sz="' + str(size).encode() + b'"'
            body = re.sub(rb"<a:(?:solidFill|effectLst)\b.*?</a:(?:solidFill|effectLst)>", b"", m.group(3), flags=re.S)
            fill = b"<a:solidFill><a:srgbClr val=\"" + color.encode() + b"\"/></a:solidFill>"
            return b"<a:" + tag + attrs + b">" + fill + body + b"</a:" + tag + b">"

        para = re.sub(rb"<a:(rPr|endParaRPr)\b([^>]*)>(.*?)</a:\1>", style_prop, para, flags=re.S)
        fragment = fragment[:paras[i].start()] + para + fragment[paras[i].end():]
    return fragment


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path, help="One-slide cover deck built from the template")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--photo-id", help="Picture shape id; defaults to the largest picture")
    ap.add_argument("--title-id", default="8")
    ap.add_argument("--kicker-id", default="3")
    ap.add_argument("--date-id", default="14")
    ap.add_argument("--kicker")
    ap.add_argument("--title", help="Two title lines separated by |")
    ap.add_argument("--subtitle")
    ap.add_argument("--date")
    ap.add_argument("--panel-width", type=float, default=0.54)
    args = ap.parse_args()
    if not args.input.is_file():
        ap.error("input cover deck does not exist")
    if not 0.45 <= args.panel_width <= 0.65:
        ap.error("panel-width must be between 0.45 and 0.65")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(args.input) as zin:
        pres = ET.fromstring(zin.read("ppt/presentation.xml"))
        size = pres.find(f"{{{P}}}sldSz")
        slides = pres.find(f"{{{P}}}sldIdLst")
        if size is None or slides is None or len(slides) != 1:
            raise ValueError("Input must be a one-slide presentation with defined dimensions")
        sw, sh = int(size.get("cx")), int(size.get("cy"))
        slide_path = "ppt/slides/slide1.xml"
        data = zin.read(slide_path)

        # Determine the largest picture without reserializing any package XML.
        root = ET.fromstring(data)
        candidates = []
        for pic in root.findall(f".//{{{P}}}pic"):
            nv = pic.find(f"{{{P}}}nvPicPr/{{{P}}}cNvPr")
            ext = pic.find(f"{{{P}}}spPr/{{{A}}}xfrm/{{{A}}}ext")
            if nv is not None and ext is not None:
                candidates.append((int(ext.get("cx", 0)) * int(ext.get("cy", 0)), nv.get("id")))
        if not candidates:
            raise ValueError("No pictures found on cover")
        photo_id = args.photo_id or max(candidates)[1]
        photo_m, photo = match_fragment(data, b"p:pic", photo_id)
        box_x = round(sw * args.panel_width)
        box_y = round(sh * 0.15)
        box_w = sw - box_x
        box_h = round(sh * 0.70)
        photo = set_xfrm(photo, box_x, box_y, box_w, box_h)
        # Crop from the left so the people at the image's right stay fully visible.
        visible_fraction = box_w / box_h * 9 / 16
        left_crop = max(0, min(round((1 - visible_fraction) * 100000), 70000))
        src_rect = b'<a:srcRect l="' + str(left_crop).encode() + b'" r="1000"/>'
        if re.search(rb"<a:srcRect\b[^>]*/>", photo):
            photo = re.sub(rb"<a:srcRect\b[^>]*/>", src_rect, photo, count=1)
        else:
            photo = re.sub(rb"</a:blip>", b"</a:blip>" + src_rect, photo, count=1)
        photo = re.sub(rb"<a:picLocks\b[^>]*/>", b"", photo)
        data = data[:photo_m.start()] + photo + data[photo_m.end():]

        # Delete a previously generated overlay shape while preserving all other XML.
        for m in reversed(list(re.finditer(rb"<p:sp\b.*?</p:sp>", data, re.S))):
            if b"Editable translucent title overlay" in m.group():
                data = data[:m.start()] + data[m.end():]

        # Hide master placeholders such as an automatic cover page number.
        root_tag = re.search(rb"<p:sld\b[^>]*>", data)
        if not root_tag:
            raise ValueError("Slide root element was not found")
        if b"showMasterSp=" not in root_tag.group():
            data = data[:root_tag.end()-1] + b' showMasterSp="0"' + data[root_tag.end()-1:]

        bg = b'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
        if b"<p:bg>" in data:
            data = re.sub(rb"<p:bg\b.*?</p:bg>", bg, data, count=1, flags=re.S)
        else:
            data = re.sub(rb"(<p:cSld\b[^>]*>)", rb"\1" + bg, data, count=1)

        # Main copy column.
        km, kicker = match_fragment(data, b"p:sp", args.kicker_id)
        kicker = set_xfrm(kicker, round(sw*.055), round(sh*.285), round(sw*.43), round(sh*.07))
        if args.kicker:
            kicker = replace_text(kicker, [args.kicker])
        kicker = style_text(kicker, "007F86", [1400])
        data = data[:km.start()] + kicker + data[km.end():]

        tm, title = match_fragment(data, b"p:sp", args.title_id)
        title = set_xfrm(title, round(sw*.055), round(sh*.36), round(sw*.43), round(sh*.30))
        if args.title:
            lines = args.title.split("|")
            title = replace_text(title, [lines[0], lines[1] if len(lines) > 1 else ""])
        if args.subtitle:
            title = replace_paragraph(title, 2, args.subtitle)
        title = style_text(title, "123B4A", [2400, 3200, 1600])
        data = data[:tm.start()] + title + data[tm.end():]

        dm, date = match_fragment(data, b"p:sp", args.date_id)
        date = set_xfrm(date, round(sw*.055), round(sh*.82), round(sw*.43), round(sh*.08))
        if args.date:
            date = replace_text(date, [args.date])
        date = style_text(date, "52636B", [1200])
        data = data[:dm.start()] + date + data[dm.end():]

        # Scale and position the World Bank mark to keep it inside the text panel.
        try:
            lm, logo = match_fragment(data, b"p:pic", "10")
            old_xfrm = re.search(rb"<a:xfrm\b[^>]*>.*?</a:xfrm>", logo, re.S)
            old_ext = re.search(rb"<a:ext\b[^>]*/>", old_xfrm.group())
            old_cx = int(re.search(rb'cx="(\d+)"', old_ext.group()).group(1))
            old_cy = int(re.search(rb'cy="(\d+)"', old_ext.group()).group(1))
            new_cx = round(sw*.245)
            new_cy = round(new_cx*old_cy/old_cx)
            logo = set_xfrm(logo, round(sw*.255), round(sh*.094), new_cx, new_cy)
            data = data[:lm.start()] + logo + data[lm.end():]
        except ValueError:
            pass  # Templates without this specific mark keep their original logo positions.

        # Ensure edited XML remains well formed without writing it back through an XML serializer.
        ET.fromstring(data)
        with ZipFile(args.output, "w", ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                zout.writestr(info, data if info.filename == slide_path else zin.read(info.filename))
    print(args.output)


if __name__ == "__main__":
    main()
