import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

def main():
    parser = argparse.ArgumentParser(description="Read image via OCR API")
    parser.add_argument("--file", required=True, help="Path to image file")
    parser.add_argument(
        "--prompt",
        default="Extract all text from this image. Preserve structure and layout.",
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument(
        "--base-url", default="http://localhost:20128/v1", help="API base URL"
    )
    args = parser.parse_args()

    api_key = os.environ.get("OMNIROUTE_API_KEY")
    if not api_key:
        print(
            "Error: OMNIROUTE_API_KEY environment variable is not set.", file=sys.stderr
        )
        sys.exit(1)

    ext = os.path.splitext(args.file)[1].lower()
    mime = MIME_MAP.get(ext)
    if not mime:
        print(
            f"Error: unsupported image extension '{ext}'. Supported: {', '.join(MIME_MAP)}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(args.file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "model": "ocr",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": args.prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
    }

    req = urllib.request.Request(
        f"{args.base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)

    try:
        text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"Unexpected response: {json.dumps(result)}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
