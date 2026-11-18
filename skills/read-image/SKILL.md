---
name: read-image
description: Read/extract text from an image via the local OCR API (http://localhost:20128/v1, model: ocr). Converts PNG/JPG/JPEG/WEBP/GIF/BMP images to extracted text using an OpenAI-compatible vision chat-completions endpoint. Use when the user wants to OCR an image, read text from a screenshot, extract text from a picture, or "read this image".
---

# read-image Skill

Extract text from image files using a local OCR API. The API is OpenAI-compatible: it accepts a base64-encoded image in a `message.content` `image_url` block and returns extracted text via the standard `choices[0].message.content` field.

## Invocation

### Windows (PowerShell)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/read-image/read_image.ps1 --file "path\to\image.png"
```

### Custom prompt (Windows)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/read-image/read_image.ps1 --file "path\to\image.png" --prompt "Extract the table data as markdown"
```

### WSL/Linux (Bash)

```bash
bash $OPENCODE_CONFIG_DIR/shared/skills/read-image/read_image.sh --file /path/to/image.png
```

### Write output to file

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/read-image/read_image.ps1 --file "img.png" --output "out.txt"
```

## Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `--file` | Yes | — | Path to the image file (PNG, JPG, JPEG, WEBP, GIF, BMP) |
| `--prompt` | No | `Extract all text from this image. Preserve structure and layout.` | Instruction sent to the OCR model |
| `--output` | No | stdout | Write extracted text to this file instead of stdout |
| `--base-url` | No | `http://localhost:20128/v1` | API base URL |

## Output

Extracted text to stdout, or to the file given by `--output`.

## Authentication

Requires the `OMNIROUTE_API_KEY` environment variable (Bearer <REDACTED>):

```powershell
$env:OMNIROUTE_API_KEY = "sk-...."
```

```bash
export OMNIROUTE_API_KEY="sk-...."
```

## API Details

- **Endpoint:** `POST {base-url}/chat/completions`
- **Model id:** `ocr`
- **Request body (JSON):**
  ```json
  {
    "model": "ocr",
    "messages": [
      {
        "role": "user",
        "content": [
          { "type": "text", "text": "<prompt>" },
          { "type": "image_url", "image_url": { "url": "data:image/png;base64,<b64>" } }
        ]
      }
    ]
  }
  ```
- **Response:** extracted text at `choices[0].message.content`.

## Notes

- Image is base64-encoded and sent as a data URI; large images increase payload size and latency.
- MIME type is inferred from the file extension.
- The API key is read from the environment — it is never stored in the skill files.
