# Reusable PowerPoint cover workflow

Requires Python 3. The PPTX builder and validator use only the Python standard library.

## 1. Build a one-slide cover from a template

```powershell
python create_cover_pptx.py `
  --template "template.pptx" `
  --cover-image "cover.png" `
  --output "cover-output.pptx" `
  --overlay-color "#002C36" `
  --overlay-transparency 55 `
  --overlay-width 1.0 `
  --replace "Old title=New title"
```

The builder leaves the source image unchanged and inserts a native editable full-slide PowerPoint rectangle above the image and below the title/logos. The dark teal rectangle holds opacity behind the title, then fades to invisible at the right edge. `--overlay-transparency` uses PowerPoint's convention: 0 is opaque and 100 is invisible. The default is 55% transparent. The cover picture and overlay rectangle remain unlocked and editable. It retains the template's package parts and content-type declarations and does not alter the source template.

## 2. Validate the package

```powershell
python validate_cover_pptx.py "cover-output.pptx"
```

Render the result and inspect it visually before delivery. Package validation does not replace visual review or opening the file in PowerPoint.

## 2. Apply an approved editorial cover redesign

First build the one-slide cover with `create_cover_pptx.py`. Then run:

```powershell
python create_editorial_cover.py `
  --input "cover-base.pptx" `
  --output "cover-editorial.pptx" `
  --title-id 8 --kicker-id 3 --date-id 14
```

The script keeps the cover image, logos, and text editable, places the image in a right-side frame, and uses a light left text column. It makes surgical XML edits to preserve the template's original PowerPoint namespace and extension markup. Supply shape IDs from the template when they differ. Validate with `validate_cover_pptx.py`, render the output, and visually inspect it.

## 3. Apply a photo treatment

Start with a clean one-slide cover and choose a treatment:

```powershell
python style_cover_photo.py `
  --input "cover-base.pptx" `
  --output "cover-styled.pptx" `
  --style circle-halo
```

Available styles are `circle-halo`, `angled-layer`, and `soft-frame`. The image crop and backing shape stay as separate editable PowerPoint objects. If the user returns to the original template design, rebuild from the untouched template and approved image instead of applying another treatment over the styled output. Validate and render the result before delivery.
