"""Convert the green-screen not-connected MP4 into a transparent Bevy sprite atlas."""

import json
import math
import os

import cv2
import numpy as np
from PIL import Image


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "avatar", "assets", "animation", "not-connected.mp4")
OUTPUT_DIR = os.path.join(ROOT, "avatar", "assets", "runtime", "bulb")
ATLAS_PATH = os.path.join(OUTPUT_DIR, "not-connected-atlas.png")
CONNECTED_ATLAS_PATH = os.path.join(OUTPUT_DIR, "connected-atlas.png")
METADATA_PATH = os.path.join(OUTPUT_DIR, "not-connected-atlas.json")

FRAME_WIDTH = 192
FRAME_HEIGHT = 288
ATLAS_COLUMNS = 12
GREEN_LOW = 24.0
GREEN_HIGH = 100.0


def smoothstep(low: float, high: float, value: np.ndarray) -> np.ndarray:
    x = np.clip((value - low) / (high - low), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    capture = cv2.VideoCapture(SOURCE)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {SOURCE}")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 24.0
    source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    columns = min(ATLAS_COLUMNS, frame_count)
    rows = (frame_count + columns - 1) // columns
    atlas = Image.new(
        "RGBA", (columns * FRAME_WIDTH, rows * FRAME_HEIGHT), (0, 0, 0, 0)
    )

    # Center crop around Bulb. This removes most empty green margin while keeping
    # every frame at one consistent crop so the animation does not jitter.
    crop_left = int(source_width * 0.29)
    crop_right = int(source_width * 0.71)
    crop_top = int(source_height * 0.025)
    crop_bottom = int(source_height * 0.975)

    frame_index = 0
    preview = None
    while True:
        ok, bgr = capture.read()
        if not ok:
            break

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        crop = rgb[crop_top:crop_bottom, crop_left:crop_right]
        height, width = crop.shape[:2]

        green_excess = crop[:, :, 1].astype(np.float32) - np.maximum(
            crop[:, :, 0].astype(np.float32), crop[:, :, 2].astype(np.float32)
        )
        alpha = 1.0 - smoothstep(GREEN_LOW, GREEN_HIGH, green_excess)

        # Reduce green spill on partially keyed edge pixels before resizing.
        decontaminated = crop.astype(np.float32)
        spill = np.maximum(
            0.0,
            decontaminated[:, :, 1]
            - np.maximum(decontaminated[:, :, 0], decontaminated[:, :, 2]),
        )
        decontaminated[:, :, 1] -= spill * 0.82
        rgba = np.dstack(
            [np.clip(decontaminated, 0, 255).astype(np.uint8), (alpha * 255).astype(np.uint8)]
        )

        image = Image.fromarray(rgba, "RGBA")
        image.thumbnail((FRAME_WIDTH - 8, FRAME_HEIGHT - 8), Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 0))
        cell.alpha_composite(
            image,
            ((FRAME_WIDTH - image.width) // 2, (FRAME_HEIGHT - image.height) // 2),
        )

        x = (frame_index % columns) * FRAME_WIDTH
        y = (frame_index // columns) * FRAME_HEIGHT
        atlas.alpha_composite(cell, (x, y))
        if frame_index == 0:
            preview = cell.copy()
        frame_index += 1

    capture.release()
    if frame_index == 0:
        raise RuntimeError("The source MP4 contained no frames")

    atlas.save(ATLAS_PATH, optimize=True)
    if preview is not None:
        preview.save(os.path.join(OUTPUT_DIR, "not-connected-preview.png"))

    generate_connected_animation(frame_count, columns)

    metadata = {
        "source": "animation/not-connected.mp4",
        "frame_count": frame_index,
        "fps": fps,
        "source_dimensions": [source_width, source_height],
        "frame_dimensions": [FRAME_WIDTH, FRAME_HEIGHT],
        "columns": columns,
        "rows": rows,
        "chroma_key": "green",
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as output:
        json.dump(metadata, output, indent=2)

    print(f"Wrote {frame_index} transparent frames to {ATLAS_PATH}")
    print(f"Wrote connected idle animation to {CONNECTED_ATLAS_PATH}")
    print(f"Atlas dimensions: {atlas.width}x{atlas.height}, {fps:g} fps")


def generate_connected_animation(frame_count: int, columns: int) -> None:
    """Render a new connected-state idle loop from connected Bulb artwork."""
    reference = Image.open(
        os.path.join(OUTPUT_DIR, "bulb-connected-idle-v1.png")
    ).convert("RGBA")
    character = reference.crop(reference.getchannel("A").getbbox())
    character.thumbnail((FRAME_WIDTH - 12, FRAME_HEIGHT - 12), Image.Resampling.LANCZOS)

    rows = (frame_count + columns - 1) // columns
    atlas = Image.new("RGBA", (columns * FRAME_WIDTH, rows * FRAME_HEIGHT), (0, 0, 0, 0))
    preview = None
    video_path = os.path.join(OUTPUT_DIR, "connected-generated.mp4")
    writer = cv2.VideoWriter(
        video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        24.0,
        (FRAME_WIDTH, FRAME_HEIGHT),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create connected-state video: {video_path}")

    for index in range(frame_count):
        phase = 2.0 * math.pi * index / frame_count
        breathe = 1.0 + 0.018 * math.sin(phase)
        width = round(character.width * breathe)
        height = round(character.height * breathe)
        pose = character.resize((width, height), Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 0))
        offset_x = round((FRAME_WIDTH - width) / 2 + 1.5 * math.sin(phase))
        offset_y = round((FRAME_HEIGHT - height) / 2 + 2.0 * math.sin(phase))
        cell.alpha_composite(pose, (offset_x, offset_y))

        x = (index % columns) * FRAME_WIDTH
        y = (index // columns) * FRAME_HEIGHT
        atlas.alpha_composite(cell, (x, y))
        if index == 0:
            preview = cell.copy()

        # A green backing makes the generated MP4 usable with chroma-key players;
        # the PNG atlas retains proper alpha for the desktop overlay.
        green_bg = Image.new("RGBA", cell.size, (0, 255, 0, 255))
        green_bg.alpha_composite(cell)
        rgb = np.array(green_bg.convert("RGB"))
        writer.write(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    writer.release()
    atlas.save(CONNECTED_ATLAS_PATH, optimize=True)
    if preview is not None:
        preview.save(os.path.join(OUTPUT_DIR, "connected-preview.png"))
    print(f"Wrote connected idle sprite animation to {CONNECTED_ATLAS_PATH}")
    print(f"Wrote generated connected idle video to {video_path}")


if __name__ == "__main__":
    main()
