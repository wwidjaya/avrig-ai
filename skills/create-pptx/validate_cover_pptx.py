#!/usr/bin/env python3
"""Check PPTX ZIP/XML integrity, slide count, and internal relationships."""
import argparse
import posixpath
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    path = parser.parse_args().pptx
    with ZipFile(path) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"FAIL: corrupt ZIP member: {bad}")
        names = set(zf.namelist())
        for name in names:
            if name.endswith((".xml", ".rels")):
                ET.fromstring(zf.read(name))
        slide_count = len(ET.fromstring(zf.read("ppt/presentation.xml")).find(f"{{{P}}}sldIdLst"))
        dangling = []
        for relpath in names:
            if not relpath.endswith(".rels"):
                continue
            source = "" if relpath == "_rels/.rels" else posixpath.join(
                relpath.rsplit("/_rels/", 1)[0], relpath.rsplit("/_rels/", 1)[1][:-5]
            )
            root = ET.fromstring(zf.read(relpath))
            for rel in root.findall(f"{{{PKG}}}Relationship"):
                if rel.get("TargetMode") == "External":
                    continue
                target = rel.get("Target", "")
                part = posixpath.normpath(target.lstrip("/") if target.startswith("/")
                                          else posixpath.join(posixpath.dirname(source), target))
                if part not in names:
                    dangling.append((relpath, target))
        if dangling:
            raise SystemExit(f"FAIL: dangling relationships: {dangling[:5]}")
    print(f"PASS: {path} | {slide_count} visible slide(s) | package/XML valid | no dangling relationships")


if __name__ == "__main__":
    main()
