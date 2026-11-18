#!/usr/bin/env python3
"""Create a one-slide cover deck from a PPTX template and a replacement image."""
import argparse
import posixpath
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("a", A)
ET.register_namespace("r", R)
ET.register_namespace("p", P)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--cover-image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--slide", type=int, default=1, help="Template slide to retain (default: 1)")
    parser.add_argument("--replace", action="append", default=[], metavar="OLD=NEW",
                        help="Replace text in slide XML; repeat for multiple strings")
    parser.add_argument("--overlay-color", default="#002C36",
                        help="Editable translucent rectangle color (default: #002C36)")
    parser.add_argument("--overlay-transparency", type=int, default=55,
                        help="Rectangle transparency from 0=opaque to 100=invisible (default: 55)")
    parser.add_argument("--overlay-width", type=float, default=1.0,
                        help="Rectangle width as a fraction of slide width (default: 1.0, full slide)")
    args = parser.parse_args()

    replacements = []
    for item in args.replace:
        if "=" not in item:
            parser.error(f"invalid --replace {item!r}; expected OLD=NEW")
        replacements.append(tuple(part.encode("utf-8") for part in item.split("=", 1)))
    color = args.overlay_color.lstrip("#")
    if len(color) != 6 or any(c not in "0123456789abcdefABCDEF" for c in color):
        parser.error("overlay-color must be a six-digit hex color")
    if not 0 <= args.overlay_transparency <= 100:
        parser.error("overlay-transparency must be between 0 and 100")
    if not 0 < args.overlay_width <= 1:
        parser.error("overlay-width must be greater than 0 and at most 1")
    if not args.template.is_file() or not args.cover_image.is_file():
        parser.error("template and cover image must exist")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(args.template) as zin:
        names = set(zin.namelist())
        pres = zin.read("ppt/presentation.xml")
        pm = re.search(rb"(<p:sldIdLst\b[^>]*>)(.*?)(</p:sldIdLst>)", pres, re.S)
        if not pm:
            raise ValueError("Presentation has no slide list")
        slide_ids = re.findall(rb"<p:sldId\b[^>]*/>|<p:sldId\b[^>]*>.*?</p:sldId>", pm.group(2), re.S)
        if not 1 <= args.slide <= len(slide_ids):
            raise ValueError(f"Slide {args.slide} is outside the template's {len(slide_ids)} slides")
        chosen = slide_ids[args.slide - 1]
        pres = pres[:pm.start()] + pm.group(1) + chosen + pm.group(3) + pres[pm.end():]

        slide_path = f"ppt/slides/slide{args.slide}.xml"
        rels_path = f"ppt/slides/_rels/slide{args.slide}.xml.rels"
        slide = zin.read(slide_path)
        for old, new in replacements:
            if old not in slide:
                raise ValueError(f"Text not found on slide {args.slide}: {old.decode('utf-8')!r}")
            slide = slide.replace(old, new, 1)

        # Add an editable rectangle directly above the full-slide photo and
        # below the cover text/logos. Its gradient softens the right edge.
        presentation = ET.fromstring(zin.read("ppt/presentation.xml"))
        slide_size = presentation.find(f"{{{P}}}sldSz")
        if slide_size is None:
            raise ValueError("Presentation has no slide dimensions")
        slide_width, slide_height = int(slide_size.get("cx")), int(slide_size.get("cy"))
        rect_width = round(slide_width * args.overlay_width)
        slide_root = ET.fromstring(slide)
        ids = [int(e.get("id")) for e in slide_root.findall(f".//{{{P}}}cNvPr") if e.get("id", "").isdigit()]
        shape_id = max(ids, default=0) + 1
        alpha = (100 - args.overlay_transparency) * 1000
        fade_start = 72000
        overlay = (
            f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Editable translucent title overlay"/>'
            f'<p:cNvSpPr/>'
            f'<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{rect_width}" cy="{slide_height}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:gradFill rotWithShape="1">'
            f'<a:gsLst><a:gs pos="0"><a:srgbClr val="{color.upper()}"><a:alpha val="{alpha}"/>'
            f'</a:srgbClr></a:gs><a:gs pos="{fade_start}"><a:srgbClr val="{color.upper()}">'
            f'<a:alpha val="{alpha}"/></a:srgbClr></a:gs><a:gs pos="100000"><a:srgbClr val="{color.upper()}">'
            f'<a:alpha val="0"/></a:srgbClr></a:gs></a:gsLst><a:lin ang="0" scaled="1"/>'
            f'</a:gradFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>'
        ).encode("utf-8")
        picture_match = re.search(rb"<p:pic\b.*?</p:pic>", slide, re.S)
        if not picture_match:
            raise ValueError("Could not locate the cover photo picture element")
        slide = slide[:picture_match.end()] + overlay + slide[picture_match.end():]

        # Find the largest picture by area; this is normally the full-slide cover.
        root = ET.fromstring(slide)
        pics = []
        for pic in root.findall(f".//{{{P}}}pic"):
            blip = pic.find(f".//{{{A}}}blip")
            ext = pic.find(f".//{{{A}}}xfrm/{{{A}}}ext")
            if blip is not None and ext is not None:
                rid = blip.get(f"{{{R}}}embed")
                area = int(ext.get("cx", 0)) * int(ext.get("cy", 0))
                pics.append((area, rid))
        if not pics:
            raise ValueError(f"No embedded pictures found on slide {args.slide}")
        image_rid = max(pics)[1]

        # Fit the replacement cover picture exactly to the slide canvas.
        # Templates often overscan the picture slightly; keeping that transform
        # would make the photo bounds differ from the full-slide overlay.
        fitted = False
        picture_pattern = re.compile(rb"<p:pic\b.*?</p:pic>", re.S)
        def fit_picture(match: re.Match[bytes]) -> bytes:
            nonlocal fitted
            fragment = match.group(0)
            wrapper = (f'<root xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}">').encode() + fragment + b"</root>"
            parsed = ET.fromstring(wrapper)
            blip = parsed.find(f".//{{{A}}}blip")
            if blip is None or blip.get(f"{{{R}}}embed") != image_rid:
                return fragment
            xfrm_match = re.search(rb"<a:xfrm\b[^>]*>.*?</a:xfrm>", fragment, re.S)
            if not xfrm_match:
                raise ValueError("Cover picture has no transform")
            xfrm = xfrm_match.group(0)
            xfrm = re.sub(rb"<a:off\b[^>]*/>", b'<a:off x="0" y="0"/>', xfrm, count=1)
            xfrm = re.sub(rb"<a:ext\b[^>]*/>", f'<a:ext cx="{slide_width}" cy="{slide_height}"/>'.encode(), xfrm, count=1)
            fragment = fragment[:xfrm_match.start()] + xfrm + fragment[xfrm_match.end():]
            # Remove any template picture locks so the replacement cover remains editable.
            fragment = re.sub(rb"<a:picLocks\b[^>]*/>", b"", fragment)
            fitted = True
            return fragment
        slide = picture_pattern.sub(fit_picture, slide)
        if not fitted:
            raise ValueError("Could not size the replacement cover picture to the slide")

        rels = zin.read(rels_path)
        rel_root = ET.fromstring(rels)
        match = next((rel for rel in rel_root.findall(f"{{{PKG}}}Relationship") if rel.get("Id") == image_rid), None)
        if match is None:
            raise ValueError(f"Image relationship {image_rid} was not found")
        image_part = "ppt/media/generated-cover.png"
        match.set("Target", "../media/generated-cover.png")
        rels = ET.tostring(rel_root, encoding="utf-8", xml_declaration=True)

        # Keep the original package graph and content type map intact. Only the
        # presentation's visible slide list, cover text, and cover image change.
        ctype = zin.read("[Content_Types].xml")
        croot = ET.fromstring(ctype)
        ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
        has_png = any(e.tag == f"{{{ct_ns}}}Default" and e.get("Extension", "").lower() == "png" for e in croot)
        if not has_png:
            croot.insert(0, ET.Element(f"{{{ct_ns}}}Default", {"Extension": "png", "ContentType": "image/png"}))
            ctype = ET.tostring(croot, encoding="utf-8", xml_declaration=True)

        with ZipFile(args.output, "w", ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "ppt/presentation.xml": data = pres
                elif info.filename == slide_path: data = slide
                elif info.filename == rels_path: data = rels
                elif info.filename == "[Content_Types].xml": data = ctype
                zout.writestr(info, data)
            zout.write(args.cover_image, image_part)
    print(args.output)


if __name__ == "__main__":
    main()
