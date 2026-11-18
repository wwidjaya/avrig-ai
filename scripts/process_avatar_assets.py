import hashlib
import json
import os
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import label

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONCEPTS_DIR = os.path.join(ROOT, "avatar", "assets", "concepts")
ANIM_DIR = os.path.join(ROOT, "avatar", "assets", "animation")
RUNTIME_DIR = os.path.join(ROOT, "avatar", "assets", "runtime", "bulb")
DEF_DIR = os.path.join(ROOT, "avatar", "definitions")


def cutout_rgba(arr_rgb: np.ndarray, is_pure_white_bg: bool = False) -> np.ndarray:
    arr = arr_rgb.astype(np.float32)
    h, w, _ = arr.shape

    if is_pure_white_bg:
        bg_model = np.array([254.0, 254.0, 254.0], dtype=np.float32)[None, None, :]
    else:
        top = arr[:30, :, :].mean(axis=(0, 1))
        bot = arr[-15:, :30, :].mean(axis=(0, 1))
        y_grad = np.linspace(0, 1, h)[:, None, None]
        bg_model = top * (1.0 - y_grad) + bot * y_grad

    diff = np.linalg.norm(arr - bg_model, axis=2)
    hsv = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1].astype(np.float32)

    gray = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy)

    y_idx = np.arange(h)[:, None]
    x_idx = np.arange(w)[None, :]
    is_left_shadow = (y_idx > int(h * 0.92)) & (x_idx < int(w * 0.20))
    is_floor = y_idx > int(h * 0.80)

    normal_bg = (diff < 16.0) & (sat < 14.0) & (grad < 15.0)
    floor_bg = is_floor & (diff < 36.0) & (sat < 12.0) & (grad < 11.0)
    shadow_bg = is_left_shadow & (diff < 65.0) & (sat < 16.0)
    is_bg_candidate = normal_bg | floor_bg | shadow_bg

    labeled, _ = label(is_bg_candidate)
    border_labels = set(
        np.unique(
            np.concatenate(
                [labeled[0, :], labeled[-1, :], labeled[:, 0], labeled[:, -1]]
            )
        )
    )
    border_labels.discard(0)

    bg_mask = np.isin(labeled, list(border_labels))
    fg_mask = ~bg_mask

    fg_labeled, fg_num = label(fg_mask)
    if fg_num > 0:
        counts = np.bincount(fg_labeled.ravel())
        counts[0] = 0
        fg_mask = fg_labeled == counts.argmax()

    inv_labeled, _ = label(~fg_mask)
    inv_border = set(
        np.unique(
            np.concatenate(
                [
                    inv_labeled[0, :],
                    inv_labeled[-1, :],
                    inv_labeled[:, 0],
                    inv_labeled[:, -1],
                ]
            )
        )
    )
    fg_mask = ~np.isin(inv_labeled, list(inv_border))

    # Feather a narrow edge band for clean anti-aliasing without leaving a pale matte.
    inside = cv2.distanceTransform(fg_mask.astype(np.uint8), cv2.DIST_L2, 3)
    outside = cv2.distanceTransform((~fg_mask).astype(np.uint8), cv2.DIST_L2, 3)
    signed_distance = inside - outside
    alpha = np.clip((signed_distance + 1.0) / 2.0, 0.0, 1.0)

    # Decontaminate semi-transparent edge RGB by estimating the local background color.
    # Fully opaque pixels retain original detail; edge pixels lose the white/gray JPG fringe.
    a = alpha[:, :, None]
    safe_a = np.maximum(a, 1.0 / 255.0)
    foreground = (arr - bg_model * (1.0 - a)) / safe_a
    foreground = np.clip(foreground, 0, 255).astype(np.uint8)
    rgba = np.dstack([foreground, (alpha * 255).astype(np.uint8)])
    return rgba


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    os.makedirs(DEF_DIR, exist_ok=True)

    # Remove old test files if present
    for tmp in ["test-base-idle.png", "test-connected-idle.png"]:
        p = os.path.join(RUNTIME_DIR, tmp)
        if os.path.exists(p):
            os.remove(p)

    outfits = ["base", "connected"]
    activities = {
        "idle": "idle",
        "listening": "listening",
        "thinking": "thinking",
        "working": "working",
        "waiting_for_user": "waiting-for-user",
        "error": "needs-attention",
    }

    target_w, target_h = 542, 726  # Crisp 2x retina size for desktop overlay (half of 1084x1451)
    manifest_assets = {}

    for outfit in outfits:
        manifest_assets[outfit] = {}
        for act_key, file_slug in activities.items():
            src_name = f"bulb-{outfit}-{file_slug}-v1.jpg"
            src_path = os.path.join(CONCEPTS_DIR, src_name)
            out_name = f"bulb-{outfit}-{file_slug}-v1.png"
            out_path = os.path.join(RUNTIME_DIR, out_name)

            im = Image.open(src_path).convert("RGB")
            rgba = cutout_rgba(np.array(im), is_pure_white_bg=False)
            pil_out = Image.fromarray(rgba, "RGBA").resize(
                (target_w, target_h), Image.Resampling.LANCZOS
            )
            # Remove only the low, neutral cast shadow to the left of the shoes.
            # Preserve the shoe itself by limiting the cleanup to gray pixels below
            # the ankle line, outside the character's shoe footprint.
            out_arr = np.array(pil_out)
            hsv_out = cv2.cvtColor(out_arr[:, :, :3], cv2.COLOR_RGB2HSV)
            yy, xx = np.ogrid[:target_h, :target_w]
            shadow_pixels = (
                (yy > int(target_h * 0.89))
                & (xx < int(target_w * 0.245))
                & (hsv_out[:, :, 1] < 32)
                & (hsv_out[:, :, 2] < 220)
            )
            out_arr[shadow_pixels, 3] = 0
            pil_out = Image.fromarray(out_arr, "RGBA")
            pil_out.save(out_path, optimize=True)

            manifest_assets[outfit][act_key] = {
                "file": f"bulb/{out_name}",
                "width": target_w,
                "height": target_h,
                "format": "png",
                "sha256": sha256_file(out_path),
                "source": f"concepts/{src_name}",
            }
            print(f"Processed {out_name}")

    # Process the 8-frame wave sheet into a clean aligned 8-frame horizontal strip
    wave_src = os.path.join(ANIM_DIR, "bulb-wave-natural-frames-v1.png")
    wave_im = Image.open(wave_src).convert("RGB")
    wave_arr = np.array(wave_im)

    row_slices = [(0, 480), (492, 972)]
    col_slices = [(0, 384), (384, 768), (768, 1152), (1152, 1536)]

    frame_w, frame_h = 384, 480
    strip = Image.new("RGBA", (frame_w * 8, frame_h), (0, 0, 0, 0))

    # Align feet baseline and horizontal center across all 8 frames
    ref_bottom = 458
    ref_center_x = 192

    for idx in range(8):
        r = idx // 4
        c = idx % 4
        r0, r1 = row_slices[r]
        c0, c1 = col_slices[c]
        cell = wave_arr[r0:r1, c0:c1]
        # Segment each frame against its white studio background using GrabCut.
        # A centered rectangle leaves a margin around Bulb, while its edge models
        # the connected background. This keeps smooth edges and excludes shadows.
        bgr = cv2.cvtColor(cell, cv2.COLOR_RGB2BGR)
        gc_mask = np.zeros(cell.shape[:2], dtype=np.uint8)
        gc_bg = np.zeros((1, 65), dtype=np.float64)
        gc_fg = np.zeros((1, 65), dtype=np.float64)
        cv2.grabCut(
            bgr,
            gc_mask,
            (18, 8, frame_w - 36, frame_h - 20),
            gc_bg,
            gc_fg,
            5,
            cv2.GC_INIT_WITH_RECT,
        )
        alpha_arr = np.where(
            (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        alpha_arr = cv2.GaussianBlur(alpha_arr, (3, 3), 0.65)
        cell_rgba = np.dstack([cell, alpha_arr])

        alpha = cell_rgba[:, :, 3]
        ys, xs = np.where(alpha > 32)
        if len(ys) > 0:
            bot_y = ys.max()
            # Use shoe region (lowest 15% of character) to find stable horizontal center
            shoe_mask = (alpha > 32) & (np.arange(cell.shape[0])[:, None] > (bot_y - 60))
            _, shoe_xs = np.where(shoe_mask)
            cx = int(np.median(shoe_xs)) if len(shoe_xs) > 0 else int((xs.min() + xs.max()) // 2)
            dy = ref_bottom - bot_y
            dx = ref_center_x - cx
        else:
            dx, dy = 0, 0

        # Remove source shadow fragments that are not part of the body silhouette.
        # Keep the largest high-alpha component, then feather its one-pixel edge.
        hard_mask = (alpha > 48).astype(np.uint8)
        components, component_count = label(hard_mask)
        if component_count:
            counts = np.bincount(components.ravel())
            counts[0] = 0
            largest = components == counts.argmax()
            alpha = np.where(largest, alpha, 0).astype(np.uint8)
            cell_rgba[:, :, 3] = alpha

        frame_img = Image.fromarray(cell_rgba, "RGBA")
        aligned = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        aligned.paste(frame_img, (dx, dy))
        strip.paste(aligned, (idx * frame_w, 0))

    wave_out_name = "bulb-base-wave-strip-v1.png"
    wave_out_path = os.path.join(RUNTIME_DIR, wave_out_name)
    strip.save(wave_out_path, optimize=True)
    print(f"Processed {wave_out_name}")

    manifest = {
        "avatar_id": "AV-01",
        "slug": "bulb",
        "name": "Bulb",
        "version": 1,
        "author": "avrig-ai",
        "license": "MIT",
        "minimum_renderer_version": "0.1.0",
        "description": "Rounded bulb-shaped PET character with luminous filament and expressive eyes.",
        "connection_outfit_mapping": {
            "not_connected": "base",
            "connecting": "base",
            "connected": "connected",
            "connection_lost": "base",
            "unknown": "base",
        },
        "outfits": {
            "base": {
                "description": "Cream T-shirt, blue jeans, and white sneakers without jacket or badge (Not Connected).",
                "has_jacket": False,
                "has_badge": False,
            },
            "connected": {
                "description": "Base outfit plus navy hoodie jacket and glowing blue shared connection chest badge (Connected).",
                "has_jacket": True,
                "has_badge": True,
            },
        },
        "states": manifest_assets,
        "animations": {
            "wave": {
                "outfit": "base",
                "file": f"bulb/{wave_out_name}",
                "frame_count": 8,
                "frame_width": frame_w,
                "frame_height": frame_h,
                "fps": 10,
                "loop": False,
                "sha256": sha256_file(wave_out_path),
                "source": "animation/bulb-wave-natural-frames-v1.png",
            }
        },
    }

    manifest_path = os.path.join(DEF_DIR, "bulb-v1.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
