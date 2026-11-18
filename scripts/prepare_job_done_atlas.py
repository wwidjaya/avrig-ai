"""Convert the green-screen job-done video into a transparent sprite atlas."""

import math
import os

import cv2
import numpy as np
from PIL import Image


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "avatar", "assets", "animation", "bulb-job-done.mp4")
OUTPUT_DIR = os.path.join(ROOT, "avatar", "assets", "runtime", "bulb")
FRAME_WIDTH = 192
FRAME_HEIGHT = 288
MAX_COLUMNS = 12


def main() -> None:
    capture = cv2.VideoCapture(SOURCE)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {SOURCE}")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    columns = min(MAX_COLUMNS, frame_count)
    rows = math.ceil(frame_count / columns)
    atlas = Image.new("RGBA", (columns * FRAME_WIDTH, rows * FRAME_HEIGHT), (0, 0, 0, 0))

    source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    left, right = int(source_width * 0.29), int(source_width * 0.71)
    top, bottom = int(source_height * 0.025), int(source_height * 0.975)

    preview = None
    index = 0
    while True:
        ok, bgr = capture.read()
        if not ok:
            break
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)[top:bottom, left:right]
        rgb_f = rgb.astype(np.float32)
        green_excess = rgb_f[:, :, 1] - np.maximum(rgb_f[:, :, 0], rgb_f[:, :, 2])
        amount = np.clip((green_excess - 24.0) / (100.0 - 24.0), 0.0, 1.0)
        amount = amount * amount * (3.0 - 2.0 * amount)
        alpha = (1.0 - amount) * 255.0

        spill = np.maximum(0.0, green_excess)
        rgb_f[:, :, 1] -= spill * 0.82
        rgba = np.dstack((np.clip(rgb_f, 0, 255).astype(np.uint8), alpha.astype(np.uint8)))
        image = Image.fromarray(rgba, "RGBA")
        image.thumbnail((FRAME_WIDTH - 8, FRAME_HEIGHT - 8), Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0, 0))
        cell.alpha_composite(image, ((FRAME_WIDTH - image.width) // 2, (FRAME_HEIGHT - image.height) // 2))
        atlas.alpha_composite(cell, ((index % columns) * FRAME_WIDTH, (index // columns) * FRAME_HEIGHT))
        if preview is None:
            preview = cell.copy()
        index += 1
    capture.release()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    atlas.save(os.path.join(OUTPUT_DIR, "job-done-atlas.png"), optimize=True)
    if preview:
        preview.save(os.path.join(OUTPUT_DIR, "job-done-preview.png"))
    print(f"Wrote {index} job-done frames to runtime/bulb/job-done-atlas.png")


if __name__ == "__main__":
    main()
