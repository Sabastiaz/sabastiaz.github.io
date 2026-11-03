#!/usr/bin/env python3
"""Generate per-quote OG preview images and landing pages for The Book of Light.

Reads the QUOTES array out of ../../book-of-light.html, renders a 1200x630
parchment card PNG per quote at pic/book-of-light/page-NNN.png, and writes
a tiny landing HTML at book-of-light/p/NNN.html with proper og:/twitter:
tags so a share into Facebook / LINE / Discord / Slack / Messenger unfurls
into the quote card instead of the generic site preview.

The landing pages immediately redirect human visitors to the main
interactive book at ../../book-of-light.html?quote=NNN&lang=both.

Run from the site root:
    python3 tools/book-of-light/build_og.py
"""
from __future__ import annotations

import json
import re
import sys
import textwrap
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "book-of-light.html"
IMG_DIR = ROOT / "pic" / "book-of-light"
LANDING_DIR = ROOT / "book-of-light" / "p"
SITE = "https://sabastiaz.lol"

# macOS system fonts
FONT_SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
FONT_SERIF_IT = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FONT_THAI = "/System/Library/Fonts/ThonburiUI.ttc"
FONT_SERIF_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"


# ── Quote extraction ────────────────────────────────────────────────────────

def extract_quotes(html: str) -> list[dict]:
    """Parse the QUOTES array literal out of the source HTML."""
    start = html.index("const QUOTES = [")
    i = html.index("[", start)
    depth = 0
    end = i
    for j in range(i, len(html)):
        c = html[j]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    literal = html[i:end]
    # The JS literal mixes single-quoted and double-quoted strings:
    #   {category:'tired',text:'…',en:"You don't have to…"}
    # A naive single-quote→double-quote pass would corrupt the apostrophes
    # inside the double-quoted strings. Walk the characters with a tiny
    # state machine instead: track which quote style we're inside and
    # only rewrite the ones that need it.
    out = []
    k = 0
    while k < len(literal):
        c = literal[k]
        if c == '"':  # already JSON-friendly, pass the whole string through
            out.append(c)
            k += 1
            while k < len(literal):
                out.append(literal[k])
                if literal[k] == '\\':
                    out.append(literal[k + 1])
                    k += 2
                    continue
                if literal[k] == '"':
                    k += 1
                    break
                k += 1
        elif c == "'":  # single-quoted → convert to double-quoted
            k += 1
            buf = []
            while k < len(literal):
                if literal[k] == '\\':
                    buf.append(literal[k + 1])
                    k += 2
                    continue
                if literal[k] == "'":
                    k += 1
                    break
                buf.append(literal[k])
                k += 1
            inner = "".join(buf)
            inner = inner.replace('\\', '\\\\')
            inner = inner.replace('"', '\\"')
            inner = inner.replace('\n', '\\n')
            out.append('"' + inner + '"')
        else:
            out.append(c)
            k += 1
    s = "".join(out)
    # Quote bare identifier keys: {category: → {"category":
    s = re.sub(r"([{,]\s*)([A-Za-z_][\w]*)\s*:", r'\1"\2":', s)
    # Strip trailing commas before } or ]
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:  # pragma: no cover - helpful debug
        snippet_start = max(0, e.pos - 80)
        snippet_end = min(len(s), e.pos + 80)
        raise SystemExit(
            f"Failed to parse QUOTES JSON at pos {e.pos}: {e.msg}\n"
            f"...{s[snippet_start:snippet_end]}..."
        ) from e


# ── Rendering ───────────────────────────────────────────────────────────────

CARD_W, CARD_H = 1200, 630
PAPER_PAD_X, PAPER_PAD_Y = 120, 70

BG_TOP = (14, 11, 9)
BG_MID = (34, 23, 12)
BG_BOT = (16, 11, 7)
PAPER_LIGHT = (247, 232, 201)
PAPER_DARK = (235, 212, 174)
PAPER_BORDER = (189, 150, 87)
INK_DARK = (72, 51, 33)
INK_MUTED = (130, 100, 71)
GOLD_LABEL = (146, 112, 68)
STAR = (181, 146, 98)


def _gradient_bg(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), BG_BOT)
    px = img.load()
    for y in range(h):
        if y < h * 0.4:
            t = y / (h * 0.4)
            r = int(BG_TOP[0] * (1 - t) + BG_MID[0] * t)
            g = int(BG_TOP[1] * (1 - t) + BG_MID[1] * t)
            b = int(BG_TOP[2] * (1 - t) + BG_MID[2] * t)
        else:
            t = (y - h * 0.4) / (h * 0.6)
            r = int(BG_MID[0] * (1 - t) + BG_BOT[0] * t)
            g = int(BG_MID[1] * (1 - t) + BG_BOT[1] * t)
            b = int(BG_MID[2] * (1 - t) + BG_BOT[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def _paper(w: int, h: int) -> Image.Image:
    pw, ph = w - PAPER_PAD_X * 2, h - PAPER_PAD_Y * 2
    paper = Image.new("RGB", (pw, ph), PAPER_LIGHT)
    px = paper.load()
    for y in range(ph):
        t = y / max(1, ph - 1)
        r = int(PAPER_LIGHT[0] * (1 - t) + PAPER_DARK[0] * t)
        g = int(PAPER_LIGHT[1] * (1 - t) + PAPER_DARK[1] * t)
        b = int(PAPER_LIGHT[2] * (1 - t) + PAPER_DARK[2] * t)
        for x in range(pw):
            px[x, y] = (r, g, b)
    d = ImageDraw.Draw(paper)
    # outer border + inner border echoing the live card
    d.rectangle([0, 0, pw - 1, ph - 1], outline=PAPER_BORDER, width=2)
    inset = 10
    d.rectangle([inset, inset, pw - 1 - inset, ph - 1 - inset],
                outline=(224, 198, 148), width=1)
    # corner diamond ornaments (Georgia-safe glyphs: `*` cluster)
    try:
        f = ImageFont.truetype(FONT_SERIF_BOLD, 22)
    except OSError:
        f = ImageFont.load_default()
    for cx, cy in [(26, 20), (pw - 42, 20), (26, ph - 46), (pw - 42, ph - 46)]:
        d.text((cx, cy), "*", fill=STAR, font=f)
    return paper


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int,
          draw: ImageDraw.ImageDraw) -> list[str]:
    """Greedy word-wrap by width. Falls back to character wrap for Thai."""
    def measure(s: str) -> int:
        bbox = draw.textbbox((0, 0), s, font=font)
        return bbox[2] - bbox[0]

    # If the text has spaces (usually English), wrap on word boundaries.
    if " " in text:
        words = text.split(" ")
        lines: list[str] = []
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if measure(trial) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
    # No spaces (Thai) → character-wrap.
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if measure(trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def render_card(index: int, quote: dict) -> Image.Image:
    img = _gradient_bg(CARD_W, CARD_H)
    paper = _paper(CARD_W, CARD_H)
    img.paste(paper, (PAPER_PAD_X, PAPER_PAD_Y))

    draw = ImageDraw.Draw(img)
    pw = CARD_W - PAPER_PAD_X * 2
    text_x = PAPER_PAD_X + 56
    text_w = pw - 112
    center_x = CARD_W // 2

    # Header: — Page NNN —
    label_font = ImageFont.truetype(FONT_SERIF_BOLD, 22)
    label = f"—  PAGE  {index + 1:03d}  —"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    draw.text((center_x - (bbox[2] - bbox[0]) // 2,
               PAPER_PAD_Y + 24), label, fill=GOLD_LABEL, font=label_font)

    cursor_y = PAPER_PAD_Y + 72

    # English quote (serif, bold-ish)
    en = f"“{quote['en']}”"
    en_font = ImageFont.truetype(FONT_SERIF_BOLD, 30)
    en_lines = _wrap(en, en_font, text_w, draw)
    for line in en_lines:
        bbox = draw.textbbox((0, 0), line, font=en_font)
        draw.text((center_x - (bbox[2] - bbox[0]) // 2, cursor_y),
                  line, fill=INK_DARK, font=en_font)
        cursor_y += 40

    # English reflection
    cursor_y += 6
    refl_en_font = ImageFont.truetype(FONT_SERIF_IT, 22)
    for line in _wrap(quote['reflectionEn'], refl_en_font, text_w, draw):
        bbox = draw.textbbox((0, 0), line, font=refl_en_font)
        draw.text((center_x - (bbox[2] - bbox[0]) // 2, cursor_y),
                  line, fill=INK_MUTED, font=refl_en_font)
        cursor_y += 30

    # Separator
    cursor_y += 10
    sep_font = ImageFont.truetype(FONT_SERIF_BOLD, 20)
    sep = "·  ·  ·"
    bbox = draw.textbbox((0, 0), sep, font=sep_font)
    draw.text((center_x - (bbox[2] - bbox[0]) // 2, cursor_y),
              sep, fill=STAR, font=sep_font)
    cursor_y += 32

    # Thai quote — Thonburi lacks curly ""; use ASCII " to avoid tofu boxes
    th = f'"{quote["text"]}"'
    th_font = ImageFont.truetype(FONT_THAI, 28)
    for line in _wrap(th, th_font, text_w, draw):
        bbox = draw.textbbox((0, 0), line, font=th_font)
        draw.text((center_x - (bbox[2] - bbox[0]) // 2, cursor_y),
                  line, fill=INK_DARK, font=th_font)
        cursor_y += 40

    # Thai reflection
    cursor_y += 2
    refl_th_font = ImageFont.truetype(FONT_THAI, 22)
    for line in _wrap(quote['reflection'], refl_th_font, text_w, draw):
        bbox = draw.textbbox((0, 0), line, font=refl_th_font)
        draw.text((center_x - (bbox[2] - bbox[0]) // 2, cursor_y),
                  line, fill=INK_MUTED, font=refl_th_font)
        cursor_y += 28

    # Credit at the bottom of the paper
    credit_font = ImageFont.truetype(FONT_SERIF_IT, 20)
    credit = "— The Book of Light · Sabastiaz"
    bbox = draw.textbbox((0, 0), credit, font=credit_font)
    draw.text((center_x - (bbox[2] - bbox[0]) // 2,
               CARD_H - PAPER_PAD_Y - 46),
              credit, fill=INK_MUTED, font=credit_font)

    return img


# ── Landing page generation ─────────────────────────────────────────────────

LANDING_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Page {num} · The Book of Light | Sabastiaz</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{site}/book-of-light.html?quote={num}&lang=both">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="The Book of Light · Sabastiaz">
  <meta property="og:url" content="{site}/book-of-light/p/{num}.html">
  <meta property="og:title" content="Page {num:03d} · The Book of Light">
  <meta property="og:description" content="{description}">
  <meta property="og:image" content="{site}/pic/book-of-light/page-{num:03d}.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="A page from The Book of Light featuring an encouraging quote in English and Thai.">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Page {num:03d} · The Book of Light">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="{site}/pic/book-of-light/page-{num:03d}.png">
  <meta http-equiv="refresh" content="0; url=../../book-of-light.html?quote={num}&lang=both">
  <style>body{{margin:0;background:#0b0908;color:#eee3c9;font:16px/1.6 Georgia,serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:24px;text-align:center}}a{{color:#f1d99e}}</style>
</head>
<body>
  <p>Opening <em>Page {num:03d}</em> of <strong>The Book of Light</strong>…</p>
  <p><a href="../../book-of-light.html?quote={num}&lang=both">Continue to the book →</a></p>
  <script>location.replace('../../book-of-light.html?quote={num}&lang=both');</script>
</body>
</html>
"""


def build_landing(index: int, quote: dict) -> str:
    num = index + 1
    desc = textwrap.shorten(
        f"“{quote['en']}” {quote['reflectionEn']}",
        width=200, placeholder="…"
    )
    return LANDING_TEMPLATE.format(
        num=num, description=escape(desc, quote=True), site=SITE
    )


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    LANDING_DIR.mkdir(parents=True, exist_ok=True)
    html = SRC.read_text(encoding="utf-8")
    quotes = extract_quotes(html)
    print(f"Parsed {len(quotes)} quotes")

    for i, q in enumerate(quotes):
        num = i + 1
        img_path = IMG_DIR / f"page-{num:03d}.png"
        land_path = LANDING_DIR / f"{num}.html"

        card = render_card(i, q)
        card.save(img_path, "PNG", optimize=True)

        land_path.write_text(build_landing(i, q), encoding="utf-8")

    print(f"Wrote {len(quotes)} images to {IMG_DIR.relative_to(ROOT)}")
    print(f"Wrote {len(quotes)} landing pages to {LANDING_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
