#!/usr/bin/env python3
"""Render a structured document model (JSON) into Confluence storage format.

The LLM authors a structured document model; this renderer deterministically
produces the Confluence storage-format HTML required by the REST API. The LLM
never writes raw storage HTML or ADF.

Storage format is used (rather than ADF) because it supports percentage *column*
widths. Confluence table `width` (``data-table-width``) is in **pixels** (ADF
spec); the reference pattern uses 1017px. Column widths in the model are given
as pixels too.

Model schema (JSON):

    {
      "title": "Page title",            # optional; used by create/update ops
      "links": {                        # optional; resolves [[wikilinks]] to URLs
        "01-Composync-Coding-Principle-Go": "https://.../pages/1052704791",
        "Composync-Coding-Standards": {"url": "https://.../pages/370573405",
                                        "title": "Coding Standards Document (CSD)"}
      },
      "sections": [
        {"heading": {"level": 2, "text": "Purpose"}},
        {"paragraph": "text with **bold**, *italic*, `code`, [link](https://...), [[wikilink]]"},
        {"bullet_list": ["a", "b"]},
        {"numbered_list": ["a", "b"]},
        {"table": {"columns": ["A", "B"], "rows": [["1", "2"]]}},
        {"roles_table": {"roles": [{"name": "...", "description": "..."}]}},
        {"code_block": {"language": "powershell", "text": "..."}},
        {"link": {"text": "KB", "href": "https://..."}},
        {"panel": {"type": "info", "text": "..."}},
        {"rule": true}
      ]
    }

Table column widths are given as **pixels** (e.g. ``"width": 86`` means 86px).
Omitted widths default to the reference pattern (table width 1017px).

Usage:
    python adf_render.py doc.json             # print storage HTML to stdout
    python adf_render.py --check doc.json     # validate + print structure errors
"""

import json
import re
import sys

BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
CODE_RE = re.compile(r"`([^`]+)`")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")

# Obsidian in-page links [[#Section Heading]] / [[#Section Heading|label]].
# Rendered as Confluence same-page anchor links (see _inpage_anchor_link).
INPAGE_RE = re.compile(r"\[\[#([^\]|]+?)(?:\|([^\]]+?))?\]\]")

# Resolves Obsidian [[wikilinks]] to Confluence page URLs + display labels.
# Populated from the model's optional "links" map by render()/render_storage().
# Unknown wikilinks are left as plain text (escaped), never rendered as broken
# anchors. Label priority: explicit [[target|label]] > link `title` >
# titles[target] > humanized target. The raw note file name is NEVER used as a
# label (see _humanize_target).
_WIKILINKS = {}
_TITLES = {}

# Same-page section anchors. Populated by render_storage()/render():
#   _PAGE_TITLE      - the model `title` (for <ri:page ri:content-title>)
#   _PAGE_ANCHORS    - normalized heading text -> anchor slug
#   _USED_ANCHORS    - set of anchor slugs referenced by [[#...]] links
_PAGE_TITLE = ""
_PAGE_ANCHORS = {}
_USED_ANCHORS = set()


def _slugify(text):
    """Make a Confluence-safe anchor name from heading text."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "section"


def _scan_inpage(model):
    """Return (anchors_map, used_anchors) for a document model.

    anchors_map maps normalized heading text -> anchor slug; used_anchors is
    the set of slugs referenced by [[#Heading|label]] in any inline text.
    """
    anchors = {}
    used = set()

    def walk(o):
        if isinstance(o, dict):
            if "heading" in o and isinstance(o["heading"], dict):
                text = o["heading"].get("text", "")
                anchors.setdefault(text.strip().casefold(), _slugify(text))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)
        elif isinstance(o, str):
            for m in INPAGE_RE.finditer(o):
                used.add(_slugify(m.group(1)))
    walk(model)
    return anchors, used


def _set_wikilinks(links):
    """Populate _WIKILINKS from the model's `links` map.

    Values may be a plain URL string (label falls back to titles[target] or a
    humanized target) or a dict {"url": ..., "title": ...} where `title` is the
    display label (the target note's frontmatter `title`). The raw note file
    name is never shown as a label.
    """
    if not isinstance(links, dict):
        raise ModelError("'links' must be an object mapping wikilink -> page URL")
    for target, value in links.items():
        if not isinstance(target, str):
            continue
        if isinstance(value, str):
            _WIKILINKS[target] = {"url": value, "title": None}
        elif isinstance(value, dict) and isinstance(value.get("url"), str):
            title = value.get("title")
            _WIKILINKS[target] = {"url": value["url"], "title": title if isinstance(title, str) else None}
        else:
            raise ModelError(f"invalid link value for {target!r}: expected URL string or {{'url', 'title'}}")


def _set_titles(titles):
    """Populate _TITLES from the model's optional `titles` map.

    Maps the wikilink target (note basename) to the note's frontmatter `title`,
    so labels show the document title instead of the note file name.
    """
    _TITLES.clear()
    if titles is None:
        return
    if not isinstance(titles, dict):
        raise ModelError("'titles' must be an object mapping wikilink -> document title")
    for target, title in titles.items():
        if isinstance(target, str) and isinstance(title, str) and title.strip():
            _TITLES[target] = title.strip()


def _humanize_target(target):
    """Turn a note file name into a readable label (never the raw file name).

    Strips a leading numeric prefix (e.g. `02-`), replaces `-`/`_` with spaces,
    and collapses whitespace. Used only when no title is available.
    """
    name = target.strip()
    if name.endswith(".md"):
        name = name[:-3]
    name = re.sub(r"^\d+\s*-\s*", "", name)
    name = re.sub(r"[-_]+", " ", name)
    return re.sub(r"\s+", " ", name).strip() or target


def _wikilink_entry(target, label):
    """Resolve a [[wikilink]] to (href, label) using the best available label.

    Label priority: explicit [[target|label]] > link `title` > titles[target] >
    humanized target. The raw note file name is never used as a label.
    """
    entry = _WIKILINKS.get(target)
    if not entry and "#" in target:
        base, _anchor = target.split("#", 1)
        entry = _WIKILINKS.get(base)
    if not entry:
        return None
    href = entry["url"]
    if label:
        return href, label
    if entry.get("title"):
        return href, entry["title"]
    if target in _TITLES:
        return href, _TITLES[target]
    return href, _humanize_target(target)


def _inpage_anchor_name(target):
    """Return the anchor slug for a [[#Heading]] target if it exists."""
    key = target.strip().casefold()
    return _PAGE_ANCHORS.get(key)


# A bare section reference label, e.g. `§3`, `§18`, `§3.1`, `§8.2`, `§4.1.3`.
_SECTION_SYMBOL_RE = re.compile(r"^\u00a7?\s*\d+(?:\.\d+)*$")


def _inpage_label(target, label):
    """Best label for a [[#Heading|label]] same-page link.

    If the explicit label is a bare section symbol (e.g. `§3`, `§18`), replace
    it with the section title (the heading text) so the link reads as the
    section, not the symbol. Otherwise the explicit label wins.
    """
    explicit = (label or "").strip()
    if explicit and _SECTION_SYMBOL_RE.match(explicit):
        return target.strip()
    return explicit or target.strip()


def _inpage_link_html(target, label):
    """Render [[#Heading|label]] as a Confluence same-page anchor link."""
    slug = _inpage_anchor_name(target)
    if slug is None:
        # Unknown heading: keep literal text, never a broken anchor.
        return _esc(f"[[#{target}" + (f"|{label}" if label else "") + "]]")
    display = _inpage_label(target, label)
    # Confluence anchor link: <ri:page> (same page) + ac:anchor fragment.
    return (f'<ac:link ac:anchor="{_esc(slug)}">'
            f'<ri:page ri:content-title="{_esc(_PAGE_TITLE)}"/>'
            f'<ac:plain-text-link-body><![CDATA[{_cdata(display)}]]></ac:plain-text-link-body>'
            f"</ac:link>")


def _anchor_macro_html(slug):
    """Confluence anchor macro, placed immediately before the target heading."""
    return (f'<ac:structured-macro ac:name="anchor" ac:schema-version="1">'
            f'<ac:parameter ac:name="">{_esc(slug)}</ac:parameter>'
            f"</ac:structured-macro>")


PANEL_TYPES = {"info", "note", "success", "warning", "error"}


class ModelError(ValueError):
    """Raised when the structured document model is invalid."""


def _inline(text):
    """Parse a string with markdown-ish inline markup into ADF inline content.

    Supports **bold**, *italic*, `code`, and [text](url) links.
    """
    if not isinstance(text, str):
        raise ModelError(f"Expected string, got {type(text).__name__}: {text!r}")

    # Tokenize by scanning for the first markdown construct left to right.
    result = []
    buf = text
    while buf:
        matches = []
        for name, regex in (
            ("bold", BOLD_RE),
            ("code", CODE_RE),
            ("link", LINK_RE),
            ("wikilink", WIKILINK_RE),
            ("italic", ITALIC_RE),
        ):
            m = regex.search(buf)
            if m:
                matches.append((m.start(), name, m))
        if not matches:
            if buf:
                result.append({"type": "text", "text": buf})
            break

        matches.sort()
        pos, name, m = matches[0]
        if pos > 0:
            result.append({"type": "text", "text": buf[:pos]})

        if name == "bold":
            result.append(
                {
                    "type": "text",
                    "text": m.group(1),
                    "marks": [{"type": "strong"}],
                }
            )
        elif name == "code":
            result.append(
                {
                    "type": "text",
                    "text": m.group(1),
                    "marks": [{"type": "code"}],
                }
            )
        elif name == "link":
            result.append(
                {
                    "type": "text",
                    "text": m.group(1),
                    "marks": [{"type": "link", "attrs": {"href": m.group(2)}}],
                }
            )
        elif name == "wikilink":
            target = m.group(1).strip()
            explicit_label = (m.group(2) or "").strip()
            resolved = _wikilink_entry(target, explicit_label)
            if resolved:
                href, label = resolved
                result.append(
                    {
                        "type": "text",
                        "text": label,
                        "marks": [{"type": "link", "attrs": {"href": href}}],
                    }
                )
            else:
                result.append({"type": "text", "text": m.group(0)})
        elif name == "italic":
            result.append(
                {
                    "type": "text",
                    "text": m.group(1),
                    "marks": [{"type": "em"}],
                }
            )
        buf = buf[m.end():]

    return result


def _paragraph(text):
    return {"type": "paragraph", "content": _inline(text)}


def _alignment_marks(align):
    if align in ("center", "right"):
        return [{"type": "alignment", "attrs": {"align": align}}]
    return None


def _styled_text_paragraph(text, bold=False, align=None):
    """Paragraph with optional strong mark and alignment mark."""
    content = _inline(text)
    if bold:
        for node in content:
            if node.get("type") == "text":
                node.setdefault("marks", []).append({"type": "strong"})
    node = {"type": "paragraph", "content": content}
    marks = _alignment_marks(align)
    if marks:
        node["marks"] = marks
    return node


def _heading(node):
    level = node.get("level", 2)
    if level not in (1, 2, 3, 4, 5, 6):
        raise ModelError(f"Invalid heading level: {level!r}")
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": _inline(node["text"]),
    }


def _heading_styled(level, text, bold=False):
    content = _inline(text)
    if bold:
        for n in content:
            if n.get("type") == "text":
                n.setdefault("marks", []).append({"type": "strong"})
    return {"type": "heading", "attrs": {"level": level}, "content": content}


def _list_item(text):
    return {
        "type": "listItem",
        "content": [{"type": "paragraph", "content": _inline(text)}],
    }


def _list(node, list_type):
    items = node
    if not isinstance(items, list) or not items:
        raise ModelError(f"{list_type} must be a non-empty list of strings")
    return {
        "type": list_type,
        "content": [_list_item(item) for item in items],
    }


DEFAULT_COLWIDTHS = [50.0, 284.0, 1465.0]
HEADER_BG = "#ffc400"
SUBROW_BG = "#DEEBFF"


def _normalize_columns(columns):
    """Return a list of column specs: {"title": str, "width": float|None}."""
    specs = []
    for c in columns:
        if isinstance(c, str):
            specs.append({"title": c, "width": None})
        elif isinstance(c, dict):
            specs.append({"title": c.get("title"), "width": c.get("width")})
        else:
            raise ModelError(f"Invalid column spec: {c!r}")
    return specs


def _cell_blocks(value):
    """Convert a cell value into a list of ADF block nodes.

    Accepts:
      - a string                       -> single paragraph
      - {"text":..., "align":..., "background":..., "bold":bool}
      - {"blocks": [<section>, ...]}   -> rendered section nodes
    """
    if isinstance(value, str):
        return [_paragraph(value)]
    if not isinstance(value, dict):
        raise ModelError(f"Invalid table cell value: {value!r}")
    if "blocks" in value:
        blocks = value["blocks"]
        if not isinstance(blocks, list) or not blocks:
            raise ModelError("cell blocks must be a non-empty list")
        return [render_node(block) for block in blocks]
    return [_styled_text_paragraph(
        value.get("text", ""),
        bold=bool(value.get("bold")),
        align=value.get("align"),
    )]


def _cell_attrs(value, colwidth, background=None):
    attrs = {"colspan": 1, "rowspan": 1, "colwidth": [colwidth]}
    if isinstance(value, dict) and value.get("background"):
        attrs["background"] = value["background"]
    elif background:
        attrs["background"] = background
    return attrs


def _table(node):
    if not isinstance(node, dict):
        raise ModelError("table must be an object with columns and rows")
    columns = node.get("columns") or []
    rows = node.get("rows") or []
    if not columns or not rows:
        raise ModelError("table requires non-empty columns and rows")

    col_specs = _normalize_columns(columns)
    ncols = len(col_specs)
    table_width = float(node.get("width", DEFAULT_TABLE_WIDTH))
    header_cells = [c["title"] if isinstance(c, dict) else c for c in columns]
    widths = _normalize_col_pxs(columns, ncols, table_width, content=[header_cells] + list(rows))

    for row in rows:
        if len(row) != ncols:
            raise ModelError(
                f"table row has {len(row)} cells, expected {ncols}"
            )

    def header_cell(spec, width):
        attrs = {"colspan": 1, "rowspan": 1, "background": HEADER_BG, "colwidth": [width]}
        content = _styled_text_paragraph(spec["title"], bold=True)
        for node in content["content"]:
            if node.get("type") == "text":
                node.setdefault("marks", []).append(
                    {"type": "textColor", "attrs": {"color": "#ffffff"}}
                )
        return {"type": "tableHeader", "attrs": attrs, "content": [content]}

    content = []
    content.append(
        {"type": "tableRow",
         "content": [header_cell(spec, widths[i]) for i, spec in enumerate(col_specs)]}
    )
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            blocks = _cell_blocks(value)
            background = SUBROW_BG if (i == 0 and isinstance(value, str) and value == "") else None
            attrs = _cell_attrs(value, widths[i], background=background)
            cells.append({"type": "tableCell", "attrs": attrs, "content": blocks})
        content.append({"type": "tableRow", "content": cells})

    return {
        "type": "table",
        "attrs": {"layout": "align-start", "width": 1800.0},
        "content": content,
    }


def _role_description_blocks(desc):
    """Convert a role description into a list of ADF blocks for a cell.

    Accepts:
      - a string                                       -> single paragraph
      - a list of {"lead": "...", "items": [...]}      -> lead paragraph + bulletList per entry
      - a list of structured-model blocks              -> rendered nodes
    """
    if isinstance(desc, str):
        return [_paragraph(desc)]
    if not isinstance(desc, list) or not desc:
        raise ModelError("role description must be a string or a non-empty list")
    blocks = []
    for entry in desc:
        if isinstance(entry, dict) and "lead" in entry:
            blocks.append(_paragraph(entry["lead"]))
            items = entry.get("items") or []
            if items:
                blocks.append(_list(items, "bulletList"))
        else:
            blocks.append(render_node(entry))
    return blocks


def _roles_table(node):
    """Render the Composync role-matrix table style.

    Main roles become numbered rows with a bold H4 name. Sub-roles become
    unnumbered rows with an empty, light-blue (#DEEBFF) number cell and an H5
    name. Descriptions support "lead paragraph -> bullet list" notation.

        {"roles_table": {
          "columns": ["No.", "Name", "Description"],   // optional
          "roles": [
            {"name": "...", "description": "...",     // or [{lead, items}, ...]
             "sub_roles": [{"name": "...", "description": "..."}]}
          ]
        }}
    """
    if not isinstance(node, dict):
        raise ModelError("roles_table must be an object with a 'roles' list")
    roles = node.get("roles")
    if not isinstance(roles, list) or not roles:
        raise ModelError("roles_table requires a non-empty 'roles' list")

    columns = node.get("columns") or ["No.", "Name", "Description"]
    col_specs = _normalize_columns(columns)
    ncols = len(col_specs)
    if ncols != 3:
        raise ModelError("roles_table requires exactly 3 columns (No., Name, Description)")
    widths = [
        (spec["width"] if spec["width"] is not None
         else DEFAULT_COLWIDTHS[i] if i < len(DEFAULT_COLWIDTHS) else 100.0)
        for i, spec in enumerate(col_specs)
    ]

    def header_cell(title, width):
        attrs = {"colspan": 1, "rowspan": 1, "background": HEADER_BG, "colwidth": [width]}
        content = _styled_text_paragraph(title, bold=True)
        for node_ in content["content"]:
            if node_.get("type") == "text":
                node_.setdefault("marks", []).append(
                    {"type": "textColor", "attrs": {"color": "#ffffff"}}
                )
        return {"type": "tableHeader", "attrs": attrs, "content": [content]}

    def num_cell(text, sub_role=False):
        if sub_role:
            attrs = {"colspan": 1, "rowspan": 1, "background": SUBROW_BG, "colwidth": [widths[0]]}
            return {"type": "tableCell", "attrs": attrs,
                    "content": [_styled_text_paragraph("", align="center")]}
        attrs = {"colspan": 1, "rowspan": 1, "colwidth": [widths[0]]}
        return {"type": "tableCell", "attrs": attrs,
                "content": [_styled_text_paragraph(str(text), align="center")]}

    def name_cell(name, level, bold):
        attrs = {"colspan": 1, "rowspan": 1, "colwidth": [widths[1]]}
        return {"type": "tableCell", "attrs": attrs,
                "content": [_heading_styled(level, name, bold=bold)]}

    def desc_cell(desc):
        attrs = {"colspan": 1, "rowspan": 1, "colwidth": [widths[2]]}
        return {"type": "tableCell", "attrs": attrs, "content": _role_description_blocks(desc)}

    content = [
        {"type": "tableRow",
         "content": [header_cell(spec["title"], widths[i]) for i, spec in enumerate(col_specs)]}
    ]
    for idx, role in enumerate(roles, start=1):
        if not isinstance(role, dict):
            raise ModelError(f"role must be an object, got {role!r}")
        content.append({"type": "tableRow", "content": [
            num_cell(idx),
            name_cell(role.get("name", ""), 4, bold=True),
            desc_cell(role.get("description")),
        ]})
        for sub in role.get("sub_roles") or []:
            if not isinstance(sub, dict):
                raise ModelError(f"sub_role must be an object, got {sub!r}")
            content.append({"type": "tableRow", "content": [
                num_cell("", sub_role=True),
                name_cell(sub.get("name", ""), 5, bold=False),
                desc_cell(sub.get("description")),
            ]})

    return {
        "type": "table",
        "attrs": {"layout": "align-start", "width": 1800.0},
        "content": content,
    }


def _code_block(node):
    text = node.get("text", "")
    language = node.get("language")
    if language is None:
        # Admonition: ADF requires a language attr; default to none.
        content = [{"type": "text", "text": text}]
        return {"type": "codeBlock", "attrs": {}, "content": content}
    return {
        "type": "codeBlock",
        "attrs": {"language": language},
        "content": [{"type": "text", "text": text}],
    }


def _panel(node):
    panel_type = node.get("type", "info")
    if panel_type not in PANEL_TYPES:
        raise ModelError(f"Invalid panel type: {panel_type!r}")
    return {
        "type": "panel",
        "attrs": {"panelType": panel_type},
        "content": [{"type": "paragraph", "content": _inline(node["text"])}],
    }


def render_node(node):
    if not isinstance(node, dict):
        raise ModelError(f"Section must be an object, got {type(node).__name__}")
    if len(node) != 1:
        raise ModelError(f"Section must have exactly one key, got {list(node)}")

    kind, payload = next(iter(node.items()))

    if kind == "heading":
        return _heading(payload)
    if kind == "paragraph":
        return _paragraph(payload)
    if kind == "bullet_list":
        return _list(payload, "bulletList")
    if kind == "numbered_list":
        return _list(payload, "orderedList")
    if kind == "table":
        return _table(payload)
    if kind == "roles_table":
        return _roles_table(payload)
    if kind == "code_block":
        return _code_block(payload)
    if kind == "link":
        return {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": payload["text"],
                    "marks": [{"type": "link", "attrs": {"href": payload["href"]}}],
                }
            ],
        }
    if kind == "panel":
        return _panel(payload)
    if kind == "rule":
        return {"type": "rule"}
    if kind == "raw":
        # Explicit escape hatch for LLM-generated ADF fragments (used by append
        # when the agent merges an existing page's ADF). Validated minimally.
        return payload
    raise ModelError(f"Unknown section type: {kind!r}")


def render(model):
    """Render a structured document model dict into ADF JSON (dict)."""
    if not isinstance(model, dict):
        raise ModelError(f"Model must be an object, got {type(model).__name__}")
    sections = model.get("sections")
    if not isinstance(sections, list):
        raise ModelError("Model requires a non-empty 'sections' list")

    links = model.get("links")
    if links is not None:
        _set_wikilinks(links)
    _set_titles(model.get("titles"))

    global _PAGE_TITLE, _PAGE_ANCHORS, _USED_ANCHORS
    _PAGE_TITLE = str(model.get("title") or "")
    _PAGE_ANCHORS, _USED_ANCHORS = _scan_inpage(model)

    content = [render_node(node) for node in sections]
    return {"type": "doc", "version": 1, "content": content}


# ---------------------------------------------------------------------------
# Storage-format renderer
# ---------------------------------------------------------------------------

# Confluence table `width` (data-table-width) is measured in PIXELS (ADF spec).
# Max width is 1800px (full-width). Reference style: yellow header, white bold
# text, align-start. Column widths are scaled to the table width.
DEFAULT_TABLE_WIDTH = 1800  # px (max)

_HTML_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def _esc(text):
    return "".join(_HTML_ESCAPES.get(ch, ch) or ch for ch in text)


def _cdata(text):
    """Encode text for a <![CDATA[...]]> block.

    CDATA is raw text — do NOT HTML-escape it (escaping would turn `&` into
    literal `&amp;`). Only the CDATA terminator `]]>` must be neutralized.
    """
    return str(text).replace("]]>", "]]&gt;")


def _inline_html(text):
    """Render markdown-ish inline markup to storage-format inline HTML.

    Supports **bold**, *italic*, `code`, and [text](url) links. HTML-escapes
    the text content.
    """
    if not isinstance(text, str):
        raise ModelError(f"Expected string, got {type(text).__name__}: {text!r}")
    out = []
    buf = text
    while buf:
        matches = []
        for name, regex in (
            ("bold", BOLD_RE),
            ("code", CODE_RE),
            ("link", LINK_RE),
            ("inpage", INPAGE_RE),
            ("wikilink", WIKILINK_RE),
            ("italic", ITALIC_RE),
        ):
            m = regex.search(buf)
            if m:
                matches.append((m.start(), name, m))
        if not matches:
            if buf:
                out.append(_esc(buf))
            break
        matches.sort()
        pos, name, m = matches[0]
        if pos > 0:
            out.append(_esc(buf[:pos]))
        if name == "bold":
            out.append(f"<strong>{_esc(m.group(1))}</strong>")
        elif name == "code":
            out.append(f"<code>{_esc(m.group(1))}</code>")
        elif name == "link":
            out.append(f'<a href="{_esc(m.group(2))}">{_esc(m.group(1))}</a>')
        elif name == "inpage":
            out.append(_inpage_link_html(m.group(1), m.group(2)))
        elif name == "wikilink":
            target = m.group(1).strip()
            explicit_label = (m.group(2) or "").strip()
            resolved = _wikilink_entry(target, explicit_label)
            if resolved:
                href, label = resolved
                out.append(f'<a href="{_esc(href)}">{_esc(label)}</a>')
            else:
                out.append(_esc(m.group(0)))
        elif name == "italic":
            out.append(f"<em>{_esc(m.group(1))}</em>")
        buf = buf[m.end():]
    return "".join(out)


def _para_html(text, align=None, bold=False, white=False):
    attrs = f' style="text-align: {align};"' if align else ""
    inner = _inline_html(text)
    if white:
        inner = f"<strong><span style=\"color: rgb(255,255,255);\">{inner}</span></strong>"
    elif bold:
        inner = f"<strong>{inner}</strong>"
    return f"<p{attrs}>{inner}</p>"


def _heading_html(level, text, with_anchor=False):
    slug = _slugify(text)
    anchor = _anchor_macro_html(slug) if with_anchor and slug in _USED_ANCHORS else ""
    return f"{anchor}<h{level}>{_inline_html(text)}</h{level}>"


def _list_html(items, ordered=False):
    tag = "ol" if ordered else "ul"
    start = ' start="1"' if ordered else ""
    lis = "".join(f"<li><p>{_inline_html(i)}</p></li>" for i in items)
    return f"<{tag}{start}>{lis}</{tag}>"


def _cell_block_html(node):
    """Render a structured-model block (section) to storage HTML."""
    kind, payload = next(iter(node.items()))
    if kind == "heading":
        return _heading_html(payload.get("level", 2), payload["text"])
    if kind == "paragraph":
        return _para_html(payload)
    if kind == "bullet_list":
        return _list_html(payload)
    if kind == "numbered_list":
        return _list_html(payload, ordered=True)
    if kind == "panel":
        return _panel_html(payload)
    if kind == "rule":
        return "<hr />"
    if kind == "code_block":
        return _code_block_html(payload)
    raise ModelError(f"Block type not allowed inside a table cell: {kind!r}")


def _cell_content_html(value):
    """Render a table cell value (string, styled dict, or blocks list) to HTML."""
    if isinstance(value, str):
        return _para_html(value)
    if not isinstance(value, dict):
        raise ModelError(f"Invalid table cell value: {value!r}")
    if "blocks" in value:
        blocks = value["blocks"]
        if not isinstance(blocks, list) or not blocks:
            raise ModelError("cell blocks must be a non-empty list")
        return "".join(_cell_block_html(b) for b in blocks)
    align = value.get("align")
    bold = bool(value.get("bold"))
    if bold:
        inner = f"<strong>{_inline_html(value.get('text', ''))}</strong>"
    else:
        inner = _inline_html(value.get("text", ""))
    attrs = f' style="text-align: {align};"' if align else ""
    return f"<p{attrs}>{inner}</p>"


def _normalize_col_pxs(columns, ncols, table_width, content=None):
    """Return a list of column widths in pixels, computed from content.

    Model `width` values are pixels (matching the reference "Principles at a
    Glance" table, which stores px). Columns without an explicit `width` are
    sized from the cell content: each column is at least as wide as its longest
    unbreakable token, then the excess table width is distributed
    proportionally to the column content (see _apply_col_minima), so a short
    column (e.g. a "No." or "Terms" column) is never crushed by a wide
    neighbour. When no `content` is supplied, columns share the table width
    equally.

    Columns with an explicit model `width` are kept at that width and are not
    re-proportioned by the content minima.
    """
    pxs = []
    explicit = set()
    for i, col in enumerate(columns):
        if isinstance(col, dict) and col.get("width") is not None:
            pxs.append(float(col["width"]))
            explicit.add(i)
        elif content is not None:
            pxs.append(_content_col_width(content, i))
        else:
            pxs.append(round(table_width / ncols, 1))
    if content is not None:
        pxs = _apply_col_minima(content, ncols, pxs, table_width, explicit)
    return pxs


# Approximate rendered pixels per text character for column sizing.
_PX_PER_CHAR = 11.0


def _apply_col_minima(content, ncols, pxs, table_width, explicit=None):
    """Enforce each column's longest-word minimum, then share the rest.

    Every column is at least `longest_word * _PX_PER_CHAR` wide. The remaining
    table width is distributed proportionally to the column content, so a short
    column (e.g. "Audience") is never crushed by a wide neighbour while long
    columns still get their fair share. If the minimums alone exceed the table
    width, they win (the table grows rather than wrapping mid-token).

    Columns flagged in `explicit` (a set of indices whose model width was set)
    keep that width and are excluded from the proportional re-distribution.
    """
    explicit = explicit or set()
    fixed = sum(pxs[i] for i in explicit)
    free = [i for i in range(ncols) if i not in explicit]
    if not free:
        return [round(p, 1) for p in pxs]
    minima = [_col_longest_word(content, i) * _PX_PER_CHAR for i in range(ncols)]
    raw = [_content_col_width(content, i) for i in range(ncols)]
    raw_total = sum(raw[i] for i in free) or 1.0

    floor = sum(minima[i] for i in free)
    if fixed + floor >= table_width - 0.5:
        for i in free:
            pxs[i] = minima[i]
        return [round(p, 1) for p in pxs]

    remainder = table_width - fixed - floor
    for i in free:
        pxs[i] = minima[i] + remainder * (raw[i] / raw_total)
    return [round(p, 1) for p in pxs]


def _col_longest_word(content, col_idx):
    """Longest unbreakable token (chars) across a column's cells."""
    return max(_cell_longest_word(row[col_idx]) for row in content)


def _cell_display_text(value):
    """Visible text of a table cell value, with [[wikilinks]] resolved to their
    display labels (so width measurement ignores the link syntax)."""
    if isinstance(value, str):
        text = value
    elif isinstance(value, dict):
        text = value.get("text", "")
    else:
        return ""
    if not isinstance(text, str):
        return ""

    def repl(m):
        target = m.group(1).strip()
        explicit = (m.group(2) or "").strip()
        if explicit:
            return explicit
        entry = _WIKILINKS.get(target)
        if entry and entry.get("title"):
            return entry["title"]
        if target in _TITLES:
            return _TITLES[target]
        return _humanize_target(target)

    return WIKILINK_RE.sub(repl, text)


def _cell_plain_len(value):
    """Approximate the visible length of a table cell value."""
    if isinstance(value, str) or isinstance(value, dict):
        return len(_cell_display_text(value))
    return 4


def _cell_longest_word(value):
    """Longest unbreakable token in a cell (approx), to avoid ugly wrapping."""
    words = []
    if isinstance(value, str) or isinstance(value, dict):
        words.append(_cell_display_text(value))
    if isinstance(value, dict) and "blocks" in value and isinstance(value["blocks"], list):
        for b in value["blocks"]:
            if isinstance(b, dict):
                for v in b.values():
                    if isinstance(v, str):
                        words.append(v)
                    elif isinstance(v, list):
                        words.extend(x for x in v if isinstance(x, str))
    if not words:
        return 1.0
    longest = 1.0
    for w in words:
        for token in w.split():
            longest = max(longest, float(len(token)))
    return longest


def _content_col_width(content, col_idx):
    """Content-driven column width (px) for one column, before scaling.

    A column is at least as wide as its longest unbreakable token, and at least
    as wide as its longest total cell text, so neither a long package name nor
    a long sentence gets crushed.
    """
    total = max(_cell_plain_len(row[col_idx]) for row in content)
    longest_word = max(_cell_longest_word(row[col_idx]) for row in content)
    return max(1.0, total, longest_word)


def _colgroup_html(pxs):
    return "".join(f'<col style="width: {p}px;" />' for p in pxs)


def _table_html(node, sub_role_bg="#DEEBFF"):
    if not isinstance(node, dict):
        raise ModelError("table must be an object with columns and rows")
    columns = node.get("columns") or []
    rows = node.get("rows") or []
    if not columns or not rows:
        raise ModelError("table requires non-empty columns and rows")
    ncols = len(columns)
    for row in rows:
        if len(row) != ncols:
            raise ModelError(f"table row has {len(row)} cells, expected {ncols}")
    width = float(node.get("width", DEFAULT_TABLE_WIDTH))
    header_cells = [c["title"] if isinstance(c, dict) else c for c in columns]
    pxs = _normalize_col_pxs(columns, ncols, width, content=[header_cells] + list(rows))
    colgroup = _colgroup_html(pxs)

    header = "".join(
        f'<th data-highlight-colour="#ffc400"><p><strong><span style="color: rgb(255,255,255);">'
        f"{_esc(col['title'] if isinstance(col, dict) else col)}"
        f"</span></strong></p></th>"
        for col in columns
    )

    body_rows = []
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            bg = ""
            if isinstance(value, dict) and value.get("background"):
                bg = f' data-highlight-colour="{_esc(value["background"])}"'
            elif i == 0 and isinstance(value, str) and value == "":
                bg = f' data-highlight-colour="{sub_role_bg}"'
            cells.append(f"<td{bg}>{_cell_content_html(value)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return (f'<table data-table-width="{width:g}" data-layout="align-start">'
            f"<colgroup>{colgroup}</colgroup><tbody><tr>{header}</tr>{''.join(body_rows)}</tbody></table>")


def _roles_table_content(roles):
    """Build a plain-text content matrix from a roles_table for width sizing.

    Mirrors the rendered rows: one row per main role (numbered) plus one row per
    sub-role. Description cells are flattened to plain text so the content-based
    column sizing has something to measure.
    """
    content = []
    for idx, role in enumerate(roles, start=1):
        if not isinstance(role, dict):
            raise ModelError(f"role must be an object, got {role!r}")
        content.append([str(idx), role.get("name", ""), _flatten_desc(role.get("description"))])
        for sub in role.get("sub_roles") or []:
            if not isinstance(sub, dict):
                raise ModelError(f"sub_role must be an object, got {sub!r}")
            content.append(["", sub.get("name", ""), _flatten_desc(sub.get("description"))])
    return content


def _flatten_desc(desc):
    """Flatten a role description (string or lead/items blocks) to plain text."""
    if isinstance(desc, str):
        return desc
    parts = []
    for entry in desc or []:
        if isinstance(entry, dict) and "lead" in entry:
            parts.append(entry.get("lead", ""))
            parts.extend(entry.get("items") or [])
        elif isinstance(entry, dict):
            for value in entry.values():
                if isinstance(value, str):
                    parts.append(value)
                elif isinstance(value, list):
                    parts.extend(v for v in value if isinstance(v, str))
    return " ".join(parts)


def _roles_table_html(node):
    if not isinstance(node, dict):
        raise ModelError("roles_table must be an object with a 'roles' list")
    roles = node.get("roles")
    if not isinstance(roles, list) or not roles:
        raise ModelError("roles_table requires a non-empty 'roles' list")
    columns = node.get("columns") or ["No.", "Name", "Description"]
    if len(columns) != 3:
        raise ModelError("roles_table requires exactly 3 columns (No., Name, Description)")
    width = float(node.get("width", DEFAULT_TABLE_WIDTH))
    header_cells = [c["title"] if isinstance(c, dict) else c for c in columns]
    content = [header_cells] + _roles_table_content(roles)
    pxs = _normalize_col_pxs(columns, 3, width, content=content)
    colgroup = _colgroup_html(pxs)
    header = "".join(
        f'<th data-highlight-colour="#ffc400"><p><strong><span style="color: rgb(255,255,255);">'
        f"{_esc(col['title'] if isinstance(col, dict) else col)}"
        f"</span></strong></p></th>"
        for col in columns
    )

    def num_cell(text, sub=False):
        if sub:
            return '<td data-highlight-colour="#DEEBFF"><p style="text-align: center;"></p></td>'
        return f"<td><p style=\"text-align: center;\">{_esc(str(text))}</p></td>"

    def name_cell(name, level, bold):
        inner = f"<strong>{_esc(name)}</strong>" if bold else _esc(name)
        return f"<td><h{level}>{inner}</h{level}></td>"

    def desc_cell(desc):
        if isinstance(desc, str):
            return f"<td>{_para_html(desc)}</td>"
        blocks = []
        for entry in desc:
            if isinstance(entry, dict) and "lead" in entry:
                blocks.append(_para_html(entry["lead"]))
                items = entry.get("items") or []
                if items:
                    blocks.append(_list_html(items))
            else:
                blocks.append(_cell_block_html(entry))
        return f"<td>{''.join(blocks)}</td>"

    rows = []
    for idx, role in enumerate(roles, start=1):
        if not isinstance(role, dict):
            raise ModelError(f"role must be an object, got {role!r}")
        rows.append(
            f"<tr>{num_cell(idx)}{name_cell(role.get('name', ''), 4, True)}{desc_cell(role.get('description'))}</tr>"
        )
        for sub in role.get("sub_roles") or []:
            if not isinstance(sub, dict):
                raise ModelError(f"sub_role must be an object, got {sub!r}")
            rows.append(
                f"<tr>{num_cell('', sub=True)}{name_cell(sub.get('name', ''), 5, False)}{desc_cell(sub.get('description'))}</tr>"
            )

    return (f'<table data-table-width="{width:g}" data-layout="align-start">'
            f"<colgroup>{colgroup}</colgroup><tbody><tr>{header}</tr>{''.join(rows)}</tbody></table>")


def _code_block_html(node):
    text = node.get("text", "")
    language = node.get("language")
    lang = f'<ac:parameter ac:name="language">{_esc(language)}</ac:parameter>' if language else ""
    return (f'<ac:structured-macro ac:name="code">'
            f"{lang}<ac:plain-text-body><![CDATA[{_cdata(text)}]]></ac:plain-text-body>"
            f"</ac:structured-macro>")


def _panel_html(node):
    panel_type = node.get("type", "info")
    if panel_type not in PANEL_TYPES:
        raise ModelError(f"Invalid panel type: {panel_type!r}")
    return (f'<ac:structured-macro ac:name="{_esc(panel_type)}">'
            f"<ac:rich-text-body>{_para_html(node['text'])}</ac:rich-text-body>"
            f"</ac:structured-macro>")


def _section_html(node):
    if not isinstance(node, dict):
        raise ModelError(f"Section must be an object, got {type(node).__name__}")
    if len(node) != 1:
        raise ModelError(f"Section must have exactly one key, got {list(node)}")
    kind, payload = next(iter(node.items()))
    if kind == "heading":
        return _heading_html(payload.get("level", 2), payload["text"], with_anchor=True)
    if kind == "paragraph":
        return _para_html(payload)
    if kind == "bullet_list":
        return _list_html(payload)
    if kind == "numbered_list":
        return _list_html(payload, ordered=True)
    if kind == "table":
        return _table_html(payload)
    if kind == "roles_table":
        return _roles_table_html(payload)
    if kind == "code_block":
        return _code_block_html(payload)
    if kind == "link":
        return f"<p><a href=\"{_esc(payload['href'])}\">{_esc(payload['text'])}</a></p>"
    if kind == "panel":
        return _panel_html(payload)
    if kind == "rule":
        return "<hr />"
    if kind == "raw":
        # Escape hatch for passing through pre-rendered storage-format HTML
        # verbatim (used when updating a page whose existing body is preserved
        # as-is apart from a few inline edits). Not HTML-escaped.
        if not isinstance(payload, str):
            raise ModelError("'raw' section must be a string of storage-format HTML")
        return payload
    raise ModelError(f"Unknown section type: {kind!r}")


def render_storage(model):
    """Render a structured document model dict into storage-format HTML (str)."""
    if not isinstance(model, dict):
        raise ModelError(f"Model must be an object, got {type(model).__name__}")
    sections = model.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ModelError("Model requires a non-empty 'sections' list")

    global _PAGE_TITLE, _PAGE_ANCHORS, _USED_ANCHORS, _WIKILINKS, _TITLES
    _PAGE_TITLE = str(model.get("title") or "")
    _PAGE_ANCHORS, _USED_ANCHORS = _scan_inpage(model)
    _WIKILINKS.clear()
    _TITLES.clear()

    links = model.get("links")
    if links is not None:
        _set_wikilinks(links)
    _set_titles(model.get("titles"))

    return "".join(_section_html(node) for node in sections)


def main(argv):
    if not argv:
        print(__doc__)
        return 1

    if argv[0] == "--check":
        if len(argv) < 2:
            print("usage: adf_render.py --check doc.json")
            return 1
        doc_path = argv[1]
        with open(doc_path, "r", encoding="utf-8") as fh:
            model = json.load(fh)
        render_storage(model)
        print("OK")
        return 0

    doc_path = argv[0]
    with open(doc_path, "r", encoding="utf-8") as fh:
        model = json.load(fh)

    print(render_storage(model))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
