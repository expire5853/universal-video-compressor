# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "Pillow==12.3.0",
# ]
# ///

"""Generate the application PNG and multi-resolution Windows icon."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRECTORY = ROOT / "assets"
PNG_PATH = ASSET_DIRECTORY / "video-compressor.png"
ICO_PATH = ASSET_DIRECTORY / "video-compressor.ico"


def interpolate(start: tuple[int, int, int], end: tuple[int, int, int], t: float):
    return tuple(round(left + (right - left) * t) for left, right in zip(start, end))


def build_icon(size: int = 1024) -> Image.Image:
    scale = size / 256

    def px(value: float) -> int:
        return round(value * scale)

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = gradient.load()
    top = (29, 61, 88)
    bottom = (16, 36, 47)
    for y in range(size):
        color = (*interpolate(top, bottom, y / max(size - 1, 1)), 255)
        for x in range(size):
            pixels[x, y] = color

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    bounds = (px(7), px(7), px(249), px(249))
    mask_draw.rounded_rectangle(bounds, radius=px(48), fill=255)
    image.alpha_composite(
        Image.composite(gradient, Image.new("RGBA", image.size), mask)
    )

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        bounds,
        radius=px(48),
        outline="#3dd6c5",
        width=px(4),
    )
    draw.rounded_rectangle(
        (px(45), px(58), px(211), px(177)),
        radius=px(20),
        fill="#0b151d",
        outline="#9ff8e9",
        width=px(9),
    )
    draw.polygon(
        [(px(105), px(88)), (px(105), px(148)), (px(157), px(118))],
        fill="#49dfcc",
    )

    line_width = px(9)
    draw.line(
        [(px(76), px(207)), (px(121), px(207))],
        fill="#6ea7c8",
        width=line_width,
    )
    draw.line(
        [(px(180), px(207)), (px(135), px(207))],
        fill="#6ea7c8",
        width=line_width,
    )
    draw.polygon(
        [(px(113), px(194)), (px(132), px(207)), (px(113), px(220))],
        fill="#6ea7c8",
    )
    draw.polygon(
        [(px(143), px(194)), (px(124), px(207)), (px(143), px(220))],
        fill="#6ea7c8",
    )
    return image


def main() -> None:
    ASSET_DIRECTORY.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    icon.save(PNG_PATH, optimize=True)
    icon.save(
        ICO_PATH,
        format="ICO",
        sizes=[
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )
    print(PNG_PATH)
    print(ICO_PATH)


if __name__ == "__main__":
    main()
