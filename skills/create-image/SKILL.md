---
name: create-image
description: >
  Plan, prompt, create, and quality-check image assets for PowerPoint, with a
  style catalog spanning corporate, enterprise architecture, photographic,
  isometric, illustration, and artistic treatments. Includes prompt templates
  and guidance for keeping the surrounding deck editable.
---

# Create Images for PowerPoint

Use this skill to choose a visual direction, write precise image prompts, generate or source visual assets, and prepare them for an editable PowerPoint workflow. Styles are descriptive controls, not a fixed list of model modes: combine visual language, subject, composition, lighting, palette, and rendering as needed.

## Working principles

- Start from the slide's message and intended use. Pick a style that supports the content, audience, and formality.
- Treat generated images as visual assets. Keep slide titles, body copy, data, labels, legends, and essential diagram structure as native editable PowerPoint objects whenever the audience may need to revise them.
- Use generated imagery for context, mood, metaphor, and non-literal backgrounds. Avoid asking an image model to render dense text, precise figures, logos, UI copy, or complex system diagrams.
- For architecture and process visuals, prefer a diagram built from editable shapes and connectors. A generated illustration can sit behind or beside it as a supporting visual.
- Preserve the user's brand palette, supplied assets, aspect ratio, safe areas, and template conventions. Do not imitate a specific living artist; translate references into general visual attributes.
- Before generating an image, recommend the single most fitting style (or a concise blend of two styles) based on the user's description, slide purpose, audience, and any supplied references. Explain the choice briefly in practical terms and show the proposed visual direction, including composition and key constraints.
- Ask the user to confirm the proposed style and direction before generation. If they request a change, revise the recommendation and confirm the revised direction. Do not treat a general request to create an image as confirmation of a specific style proposal.
- Ask only for missing choices that materially affect the recommendation or final image. When details are missing but not essential, state reasonable assumptions as part of the proposal so the user can confirm them.

## Selection workflow

1. Identify slide role: cover, section divider, concept explainer, architecture diagram, evidence/chart page, or supporting photo.
2. Identify audience and tone: executive, institutional/regulatory, technical, public-facing, or editorial.
3. Infer the best style from the description and catalog. Choose one base style or a concise blend of at most two compatible styles.
4. Propose that style to the user before generation. Briefly connect it to their subject, audience, and slide purpose; describe the intended composition, palette/rendering, text-safe area, and any assumptions. Ask for confirmation.
5. If the user confirms, define the final subject, focal point, composition, crop, palette, lighting/material, background, and text-safe area. If they ask for changes, revise and confirm again before generating.
6. Decide editability: image-only asset, image plus editable overlay, or fully native editable diagram. Keep the image separate from overlays and text.
7. Generate/source only after confirmation, then inspect at slide size and revise using the QA checklist.

## Style catalog

### A. Executive and corporate

| Style | Visual character | Good fit |
|---|---|---|
| **01. Executive Minimal** | White space, restrained geometry, few accents | Board and executive slides |
| **02. Consulting Infographic** | Clear hierarchy, structured blocks, crisp visual grouping | Strategy and recommendations |
| **03. Premium Corporate** | Polished, subtle depth, refined materials | Annual reports and leadership presentations |
| **04. Flat Corporate** | Simple vector-like shapes, limited depth | Processes and straightforward concepts |
| **05. Editorial Business** | Magazine-quality art direction and composition | Industry trends and thought leadership |
| **06. Institutional Report** | Formal, conservative, legible, information-aware | Government, regulatory, OJK, and policy reports |

For regulatory or OJK-facing work, pair **Institutional Report** with **Consulting Infographic**: formal typography and restrained color with strong information hierarchy.

### B. Enterprise architecture (six recommended styles)

These six are the recommended starting set for architecture visuals. The original catalog's most relevant set for IRS/APOLO/CAM diagrams is styles **07, 11, 13, 15**, with 08 and 09 useful for layers and stakeholder ecosystems.

| Style | Visual structure | Best use |
|---|---|---|
| **07. 2D Enterprise Architecture** | Flat, labeled components and directional connectors on a clean grid | Application/system landscape; IRS/APOLO/CAM overview |
| **08. Layered Architecture** | Horizontal tiers such as Business → Data → Application → Technology | Capability and platform stack; responsibility boundaries |
| **09. Ecosystem Map** | Organizations, users, platforms, and external parties arranged by relationship | Stakeholder context, boundaries, partner interactions |
| **11. Integration Architecture** | Systems, APIs, events, gateways, and explicit data directions | Interface and message flows; IRS/APOLO/CAM integration |
| **13. Security Architecture** | Trust zones, identities, controls, and protected assets | IAM, DevSecOps, security control views |
| **15. Hybrid Architecture** | On-premises, cloud, and SaaS zones with controlled connections | Deployment topology and migration states |

Other architecture options in the broader catalog:

| Style | Best use |
|---|---|
| **10. Capability Map** | Business capabilities and maturity or ownership groupings |
| **12. Data Architecture** | Sources, stores, transformations, governance, and data flows |
| **14. Infrastructure Architecture** | Compute, network, storage, environments, and hosting topology |

For a detailed technical architecture, use a generated visual only as a high-level metaphor or background. Build exact boxes, labels, boundaries, line styles, and arrowheads with editable PowerPoint shapes; label every flow and distinguish direction from association.

### C. Realistic and photographic

- Photorealistic
- Cinematic photography / film still
- Studio photography
- Corporate photography
- Product photography
- Documentary photography
- Editorial photography
- Architectural photography
- Aerial / drone photography

Use for people, products, workplaces, cities, and real-world scenarios. Specify subject authenticity, camera viewpoint, lighting, crop, and negative space. Avoid visual clichés and staged handshakes unless explicitly wanted.

### D. 3D and isometric

- 3D isometric
- Isometric technical illustration
- 3D clay render
- 3D corporate illustration
- 3D glossy
- 3D matte
- Low-poly 3D
- Architectural 3D render
- Diorama
- Miniature world

Useful for infrastructure, data centers, networks, data flows, AI, and DevSecOps concepts. Keep geometry simple and the camera angle consistent. Use restrained materials for institutional decks; high-gloss effects can reduce legibility and feel decorative.

### E. Corporate and conceptual illustration

- Consulting-style infographic
- Enterprise architecture illustration
- Strategy framework illustration
- Executive infographic
- Flat corporate illustration
- Minimal business illustration
- Editorial conceptual illustration
- Line-art technical illustration
- Abstract geometric concept visual

Prefer these for abstract concepts when photography would imply a literal situation that is not evidenced.

## Prompt templates

### 1. PowerPoint image asset

```text
Create a [style] visual asset for a [slide role] in a [audience/tone] PowerPoint.
Subject: [specific subject and essential elements].
Message to support: [one-sentence takeaway; do not render this as text].
Composition: [focal point, viewpoint, balance, foreground/midground/background].
Layout: [16:9 / portrait / square], with [left/right/top] kept uncluttered for editable slide title or copy.
Palette: [brand colors and neutrals]. Lighting/material: [details].
Rendering: [realism/line weight/detail level]. Background: [description].
Constraints: no text, labels, numbers, logos, watermarks, UI, or invented data; clean edges;
strong contrast at presentation size; no essential subject in the crop-safe margins.
Deliver as [format/background requirement].
```

### 2. Architecture concept illustration (supporting visual, not the authoritative diagram)

```text
Create a clean [2D / isometric / 3D matte] conceptual illustration supporting an editable
PowerPoint diagram about [architecture topic]. Show only these concepts: [list].
Arrange them in [zones/layers/flow] with clear visual separation and consistent scale.
Use [palette], a [viewpoint], and a quiet [background]. Leave [area] open for native PowerPoint
labels and annotations. No text, pseudo-labels, numbers, logos, arrows that imply undocumented
flows, invented system components, or decorative interface screens. 16:9 composition.
```

### 3. Editorial/corporate cover image

```text
Create a [photorealistic / editorial / architectural] cover image for a [topic] presentation
to [audience]. The image should evoke [mood/message] through [subject/metaphor].
Composition: [subject placement]; keep [left/right] [percentage or area] quiet and low-detail
for editable title text. Use [lighting], [palette], and [lens/material treatment].
Wide 16:9 crop, with important content inside the central safe area. No text, logos, watermarks,
charts, or UI. Avoid [specific unwanted motifs].
```

### 4. Revision prompt

```text
Keep the subject, style, viewpoint, and overall composition. Change only [specific change].
Preserve [elements]. Reduce/remove [problem]. Keep [text-safe area], palette, aspect ratio,
and crop unchanged. Do not add text, labels, logos, or new objects.
```

## Editable PowerPoint workflow

- **Native editable first:** create architecture, process, data, and organizational diagrams with PowerPoint shapes, connectors, text, tables, and charts.
- **Image as support:** use generated images for a cover, section divider, contextual photograph, or conceptual illustration. Keep the image as a separate picture object.
- **Overlay separately:** titles, gradients/solid panels, labels, and callouts should be separate editable objects. Keep them selectable, movable, and resizable.
- **Data stays native:** charts and numeric comparisons belong in editable charts/tables; never rely on image-generated values.
- **Avoid flattening:** do not rasterize an entire slide to make it look polished if the user expects to edit it. If a complex illustration must be raster, keep its accompanying labels and legend native.
- **Respect template:** match canvas dimensions, margins, typography, contrast, and image treatment. Check crop behavior and text-safe area in the actual layout.

## QA checklist

### Image quality

- Does the image reinforce the slide's one-sentence message?
- Is the focal subject obvious at normal presentation size?
- Is the composition suitable for the intended crop and text placement?
- Are edges, hands, objects, perspective, reflections, and repeated patterns plausible and clean?
- Are there accidental letters, pseudo-text, watermarks, logos, or unsupported details?
- Does the contrast and color remain legible on the slide background and projector?
- Is the image resolution sufficient for the rendered size without needless oversized files?

### PowerPoint integration

- Does the image fit the slide's aspect ratio without distorting the subject?
- Is it positioned/cropped intentionally, with focal content clear of likely crop loss?
- Are titles, labels, key facts, legend, source notes, and controls editable PowerPoint objects?
- Do image and overlays remain separately selectable?
- Does the visual remain clear in grayscale or for common color-vision deficiencies where relevant?
- Is the image licensed/approved for the intended use, and are supplied marks used only as authorized?

### Architecture-specific QA

- Are components, zones, boundaries, and flows factually supplied rather than invented?
- Does each arrow have a clear direction and meaning? Are association and data flow visually distinct?
- Are system names, trust boundaries, and layer order editable and consistent?
- Is detail density appropriate for a slide? Split a dense diagram into overview and detail slides.
- Can a reviewer revise component names and connections without regenerating the image?

Inspect the rendered slide at full size and in a contact sheet. Repair crop, contrast, alignment, collision, and legibility issues; then render again. Do not claim native PowerPoint verification unless the deck was actually opened or rendered in PowerPoint-compatible tooling.

## Quick selection guide

| Need | Start with |
|---|---|
| Board-level concept | Executive Minimal or Premium Corporate |
| Strategy recommendation | Consulting Infographic |
| Formal regulatory/OJK report | Institutional Report + Consulting Infographic |
| App/system inventory | 2D Enterprise Architecture |
| Platform layers | Layered Architecture |
| Partners, agencies, or stakeholders | Ecosystem Map |
| API/message flows | Integration Architecture |
| IAM, zones, controls | Security Architecture |
| Cloud plus on-premises | Hybrid Architecture |
| Data-center/infrastructure concept | Isometric technical illustration or Infrastructure Architecture |
| Real-world context | Editorial, documentary, or architectural photography |
| Abstract, non-literal concept | Editorial conceptual or flat corporate illustration |

