#!/usr/bin/env python3
"""Confluence Cloud connector — semantic operations on Confluence pages.

Reads credentials from confluence.env next to this script and talks to the
Confluence Cloud REST v2 API. Exposes safe, semantic subcommands only; the raw
HTTP layer is not exposed to the agent.

Subcommands:
    space resolve [--key KEY]                     resolve space key -> id
    search       -q "text" [--limit N]            search pages within the space
    get          -page-id N                        read page (title/version/body)
    create       -title T [-parent-id N] -doc FILE create page from structured doc
    update       -page-id N -title T -version N -doc FILE   version-checked update
    append       -page-id N -doc FILE              read, merge section, update

Env (confluence.env, gitignored):
    CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL,
    CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import io

import adf_render

_stdout_buffer = getattr(sys.stdout, "buffer", None)
if _stdout_buffer is not None:
    sys.stdout = io.TextIOWrapper(_stdout_buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(
        getattr(sys.stderr, "buffer", _stdout_buffer), encoding="utf-8", errors="replace"
    )


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "confluence.env")
    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    for var in ("CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN", "CONFLUENCE_SPACE_KEY"):
        env.setdefault(var, os.environ.get(var, ""))
    missing = [v for v in ("CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN") if not env[v]]
    if missing:
        sys.exit(f"error: missing Confluence credentials in confluence.env: {', '.join(missing)}")
    return env


def make_request(env, method, path, payload=None) -> "tuple[int, dict]":
    url = env["CONFLUENCE_BASE_URL"].rstrip("/") + path
    headers = {
        "Accept": "application/json",
        "Authorization": "Basic " + base64.b64encode(
            f'{env["CONFLUENCE_EMAIL"]}:{env["CONFLUENCE_API_TOKEN"]}'.encode("utf-8")
        ).decode("ascii"),
        "User-Agent": "kb-integrate-confluence/1.0",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return resp.status, parsed if isinstance(parsed, dict) else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        return exc.code, err if isinstance(err, dict) else {"message": str(err)}


def api(env, method, path, payload=None):
    status, data = make_request(env, method, path, payload)
    return status, data if isinstance(data, dict) else {}


def cmd_space_resolve(env, args):
    key = args.key or env["CONFLUENCE_SPACE_KEY"]
    status, data = api(env, "GET", f"/wiki/rest/api/space/{urllib.parse.quote(key)}")
    if status != 200:
        sys.exit(f"error: space lookup failed (HTTP {status}): {data.get('message', data)}")
    space_id = data.get("id")
    if space_id is None:
        sys.exit(f"error: space '{key}' not found")
    print(f"space_id={space_id} key={data.get('key')} name={data.get('name')} url={data.get('_links', {}).get('webui', '')}")
    return space_id


def cmd_search(env, args):
    query = args.q
    space_key = args.space or env["CONFLUENCE_SPACE_KEY"]
    cql = f'type=page AND space="{space_key}" AND (title ~ "{query}" OR text ~ "{query}")'
    params = urllib.parse.urlencode({"cql": cql, "limit": args.limit, "expand": "space"})
    status, data = api(env, "GET", f"/wiki/rest/api/content/search?{params}")
    if status != 200:
        sys.exit(f"error: search failed (HTTP {status}): {data.get('message', data)}")
    results = data.get("results", [])
    if not results:
        print("no results")
        return
    for c in results:
        cid = c.get("id", "").split("/")[-1] if c.get("id") else ""
        print(f"page_id={cid} title={c.get('title')!r}")
    print(f"({len(results)} result(s))")


def _extract_storage(page):
    body = page.get("body") or {}
    entry = body.get("storage") or {}
    value = entry.get("value")
    if value is None:
        value = body.get("value")
    return value


def cmd_get(env, args):
    params = urllib.parse.urlencode({"body-format": "storage"})
    status, data = api(env, "GET", f"/wiki/api/v2/pages/{args.page_id}?{params}")
    if status != 200:
        sys.exit(f"error: get page failed (HTTP {status}): {data.get('message', data)}")
    version = (data.get("version") or {}).get("number")
    parent = data.get("parentId", "")
    space = data.get("spaceId", "")
    print(f"page_id={data.get('id')} title={data.get('title')!r} version={version} parent_id={parent} space_id={space}")
    print(f"url={env['CONFLUENCE_BASE_URL'].rstrip('/')}/wiki/spaces/{env['CONFLUENCE_SPACE_KEY']}/pages/{data.get('id')}")
    storage = _extract_storage(data)
    if args.body == "json" and storage is not None:
        print("--- BODY (storage) ---")
        print(storage)
    elif args.body == "none":
        pass
    else:
        print("--- BODY (storage) ---")
        print(storage)
    return data


def _render_doc(args):
    if not args.doc:
        sys.exit("error: -doc FILE is required")
    with open(args.doc, "r", encoding="utf-8") as fh:
        model = json.load(fh)
    try:
        return adf_render.render(model)
    except adf_render.ModelError as exc:
        sys.exit(f"error: invalid document model: {exc}")


def _body_payload_adf(node):
    return {"representation": "adf", "object": node}


def _model_title(args):
    """Read the `title` field from the structured doc model JSON (if any)."""
    if not args.doc:
        return None
    try:
        with open(args.doc, "r", encoding="utf-8") as fh:
            return json.load(fh).get("title")
    except (OSError, json.JSONDecodeError):
        return None


def _page_title(args, existing=None):
    """Resolve the Confluence page title.

    Order: explicit -title argument > model `title` > existing page title.
    """
    return args.title or _model_title(args) or existing


def _body_payload(node):
    return {"representation": "atlas_doc_format", "value": json.dumps(node, ensure_ascii=False)}


FULL_WIDTH_KEYS = ("content-appearance-draft", "content-appearance-published")


def _set_full_width(env, page_id):
    """Set the page layout to full-width (max width) via content properties.

    Confluence Cloud stores the page layout as a content property, not in the
    body. New pages default to fixed width; setting both the draft and published
    `content-appearance-*` properties to `full-width` makes the page render at
    maximum width.
    """
    for key in FULL_WIDTH_KEYS:
        status, data = api(env, "POST", f"/wiki/api/v2/pages/{page_id}/properties",
                           {"key": key, "value": "full-width"})
        if status not in (200, 201):
            print(f"warning: could not set {key}=full-width (HTTP {status}): {data.get('message', data)}")


def cmd_set_full_width(env, args):
    _set_full_width(env, args.page_id)
    print(f"set full-width on page_id={args.page_id}")


def cmd_create(env, args):
    space_id = args.space_id or cmd_space_resolve(env, argparse.Namespace(key=None))
    adf = _render_doc(args)
    title = _page_title(args)
    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": _body_payload(adf),
    }
    if args.parent_id:
        payload["parentId"] = str(args.parent_id)
    status, data = api(env, "POST", "/wiki/api/v2/pages", payload)
    if status not in (200, 201):
        sys.exit(f"error: create page failed (HTTP {status}): {data.get('message', data)}")
    page_id = data.get("id")
    if not getattr(args, "no_full_width", False):
        _set_full_width(env, page_id)
    print(f"created page_id={page_id} title={data.get('title')!r} version={(data.get('version') or {}).get('number')}")
    print(f"url={env['CONFLUENCE_BASE_URL'].rstrip('/')}/wiki/spaces/{env['CONFLUENCE_SPACE_KEY']}/pages/{page_id}")
    return data


def cmd_update(env, args):
    adf = _render_doc(args)
    expected = args.version
    status, data = api(env, "GET", f"/wiki/api/v2/pages/{args.page_id}")
    if status != 200:
        sys.exit(f"error: read page before update failed (HTTP {status}): {data.get('message', data)}")
    actual = (data.get("version") or {}).get("number") or 0
    if expected is not None and actual != expected:
        print(json.dumps(
            {"error": "VERSION_CONFLICT", "page_id": args.page_id,
             "expected_version": expected, "actual_version": actual},
            indent=2))
        sys.exit(2)
    next_version = (actual if expected is None else expected) + 1
    payload = {
        "id": str(args.page_id),
        "status": "current",
        "title": _page_title(args, data.get("title")),
        "version": {"number": next_version},
        "body": _body_payload(adf),
    }
    status, data = api(env, "PUT", f"/wiki/api/v2/pages/{args.page_id}", payload)
    if status == 409:
        print(json.dumps(
            {"error": "VERSION_CONFLICT", "page_id": args.page_id,
             "expected_version": expected, "actual_version": (data.get("data") or {}).get("version")},
            indent=2))
        sys.exit(2)
    if status not in (200, 204):
        sys.exit(f"error: update page failed (HTTP {status}): {data.get('message', data)}")
    page_id = data.get("id") if isinstance(data, dict) else args.page_id
    print(f"updated page_id={page_id} version={next_version}")
    print(f"url={env['CONFLUENCE_BASE_URL'].rstrip('/')}/wiki/spaces/{env['CONFLUENCE_SPACE_KEY']}/pages/{page_id}")
    return data


def cmd_append(env, args):
    # Read current page, append rendered HTML to the existing storage body.
    status, data = api(env, "GET", f"/wiki/api/v2/pages/{args.page_id}?{urllib.parse.urlencode({'body-format': 'storage'})}")
    if status != 200:
        sys.exit(f"error: read page before append failed (HTTP {status}): {data.get('message', data)}")
    existing = _extract_storage(data)
    if existing is None:
        sys.exit("error: page has no body to append to")
    new_html = _render_doc(args)
    actual = (data.get("version") or {}).get("number") or 0

    payload = {
        "id": str(args.page_id),
        "status": "current",
        "title": data.get("title"),
        "version": {"number": actual + 1},
        "body": _body_payload(existing + new_html),
    }
    status, data = api(env, "PUT", f"/wiki/api/v2/pages/{args.page_id}", payload)
    if status == 409:
        print(json.dumps(
            {"error": "VERSION_CONFLICT", "page_id": args.page_id,
             "expected_version": actual + 1, "actual_version": None},
            indent=2))
        sys.exit(2)
    if status not in (200, 204):
        sys.exit(f"error: append failed (HTTP {status}): {data.get('message', data)}")
    print(f"appended page_id={args.page_id} version={actual + 1}")
    print(f"url={env['CONFLUENCE_BASE_URL'].rstrip('/')}/wiki/spaces/{env['CONFLUENCE_SPACE_KEY']}/pages/{args.page_id}")
    return data


def build_parser():
    parser = argparse.ArgumentParser(prog="confluence-tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("space", help="resolve space")
    spg = sp.add_subparsers(dest="space_cmd", required=True)
    resolve = spg.add_parser("resolve", help="space key -> id")
    resolve.add_argument("--key", default=None, help="space key (default: CONFLUENCE_SPACE_KEY)")
    resolve.set_defaults(func=cmd_space_resolve)

    s = sub.add_parser("search", help="search pages")
    s.add_argument("-q", required=True, help="search text")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--space", default=None, help="space key (default: CONFLUENCE_SPACE_KEY)")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="read a page")
    g.add_argument("-page-id", dest="page_id", required=True, help="Confluence page ID")
    g.add_argument("--body", default="json", choices=["json", "none"], help="body output")
    g.set_defaults(func=cmd_get)

    c = sub.add_parser("create", help="create a page")
    c.add_argument("-title", dest="title", default=None, help="page title (default: model `title`)")
    c.add_argument("-parent-id", dest="parent_id", default=None)
    c.add_argument("-doc", dest="doc", required=True, help="structured doc JSON file")
    c.add_argument("-space-id", dest="space_id", default=None)
    c.add_argument("-no-full-width", "--no-full-width", dest="no_full_width", action="store_true",
                   help="create the page at fixed width (default: full-width/max)")
    c.set_defaults(func=cmd_create)

    u = sub.add_parser("update", help="update a page")
    u.add_argument("-page-id", dest="page_id", required=True)
    u.add_argument("-title", dest="title", default=None)
    u.add_argument("-version", dest="version", type=int, default=None, help="expected current version")
    u.add_argument("-doc", dest="doc", required=True)
    u.set_defaults(func=cmd_update)

    a = sub.add_parser("append", help="append a section to a page")
    a.add_argument("-page-id", dest="page_id", required=True)
    a.add_argument("-doc", dest="doc", required=True)
    a.set_defaults(func=cmd_append)

    f = sub.add_parser("full-width", help="set a page layout to full-width (max width)")
    f.add_argument("-page-id", dest="page_id", required=True)
    f.set_defaults(func=cmd_set_full_width)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    env = load_env()
    args.func(env, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
