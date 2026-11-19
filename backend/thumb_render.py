"""Thumbnail pictures: a real video frame, an optional headline on a brand strip, 1280x720 JPEG under 2 MB.
Pure Pillow, runs locally, needs no AI. Arabic is shaped and reordered so it reads right to left."""
import io
from functools import lru_cache
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1280, 720
ASSETS = Path(__file__).parent / "assets"
GREEN, ACCENT, INK = (0, 117, 96), (0, 163, 127), (15, 31, 28)  # DEWA green, a lighter edge line, cool near-black
STYLES = ("band", "scrim", "none")
MAX_BYTES = 1_900_000  # YouTube's help page says 2 MB


def has_arabic(text: str) -> bool:
    return any("؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ" for c in text)


@lru_cache(maxsize=48)
def _font(arabic: bool, size: int) -> ImageFont.FreeTypeFont:
    if arabic:
        return ImageFont.truetype(str(ASSETS / "fonts/NotoSansArabic-Bold.ttf"), size)
    f = ImageFont.truetype(str(ASSETS / "fonts/Figtree-Variable.ttf"), size)
    f.set_variation_by_axes([800])
    return f


def _shape(text: str, arabic: bool) -> str:
    return get_display(arabic_reshaper.reshape(text)) if arabic else text


def _lines(text: str, arabic: bool, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(_shape(trial, arabic)) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])


def _ink(font, lines: list[str], arabic: bool) -> tuple[int, int]:
    """Real letter heights above and below the baseline. Arabic and Latin fonts differ a lot, so measure instead of guessing."""
    boxes = [font.getbbox(_shape(x, arabic), anchor="ls") for x in lines]
    return max(-b[1] for b in boxes), max(b[3] for b in boxes)


def _fit(text: str, arabic: bool, max_w: int, max_h: int):
    """Largest font (112 down to 40 px) that keeps the headline within two lines and the strip height."""
    for size in range(112, 39, -4):
        font = _font(arabic, size)
        lines = _lines(text, arabic, font, max_w)
        if not lines:
            break
        up, down = _ink(font, lines, arabic)
        if len(lines) <= 2 and len(lines) * (up + down + 14) <= max_h and all(font.getlength(_shape(x, arabic)) <= max_w for x in lines):
            return font, lines
    font = _font(arabic, 40)
    return font, _lines(text, arabic, font, max_w)[:2]


def _canvas(frame: Image.Image) -> Image.Image:
    """16:9 background. A vertical or square frame sits sharp in the middle of a blurred, darkened copy of itself."""
    if frame.width / frame.height >= 1.6:
        return ImageOps.fit(frame, (W, H), Image.LANCZOS)
    bg = ImageOps.fit(frame, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", (W, H), INK), 0.35)
    fg = ImageOps.contain(frame, (W, H), Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    return bg


def _headline(img: Image.Image, text: str, style: str) -> None:
    arabic, pad = has_arabic(text), 48
    font, lines = _fit(text, arabic, W - 2 * pad, 230)
    up, down = _ink(font, lines, arabic)
    lh = up + down + 14
    top = H - (len(lines) * lh - 14 + 64)  # strip hugs the letters: 32 px above and below
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([0, top, W, H], fill=(*GREEN, 255) if style == "band" else (*INK, 178))
    if style == "band":
        d.rectangle([0, top - 6, W, top], fill=(*ACCENT, 255))
    for i, line in enumerate(lines):
        base = top + 32 + up + i * lh  # baseline, so tall letters are never cut off
        shaped = _shape(line, arabic)
        if arabic:
            d.text((W - pad, base), shaped, font=font, fill=(255, 255, 255, 255), anchor="rs")  # white = contrast text on a filled strip
        else:
            d.text((pad, base), shaped, font=font, fill=(255, 255, 255, 255), anchor="ls")
    img.alpha_composite(layer)


def _logo(img: Image.Image) -> None:
    logo = Image.open(ASSETS / "dewa-logo.png").convert("RGBA")
    h = 52
    logo = logo.resize((int(logo.width * h / logo.height), h), Image.LANCZOS)
    white = Image.new("RGBA", logo.size, (255, 255, 255, 255))
    white.putalpha(logo.getchannel("A"))
    chip = Image.new("RGBA", (logo.width + 32, h + 24), (*INK, 170))
    chip.alpha_composite(white, (16, 12))
    img.alpha_composite(chip, (32, 28))


def render(frame_path: Path, headline: str = "", style: str = "band", logo: bool = False) -> bytes:
    """The finished JPEG. No headline (or style "none") gives the plain frame."""
    style = style if style in STYLES else "band"
    with Image.open(frame_path) as raw:
        img = _canvas(ImageOps.exif_transpose(raw).convert("RGB")).convert("RGBA")
    text = " ".join(headline.split())[:60]
    if text and style != "none":
        _headline(img, text, style)
    if logo:
        _logo(img)
    rgb = img.convert("RGB")
    for q in (90, 84, 78, 72, 66, 60):
        buf = io.BytesIO()
        rgb.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= MAX_BYTES:
            break
    return buf.getvalue()
