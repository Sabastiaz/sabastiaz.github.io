"""ปั้น prompt ภาษาอังกฤษสำหรับเอาไปวางใน ChatGPT เพื่อ gen ภาพ"""
from __future__ import annotations

import textwrap

import style
from paths import INCOMING_DIR, rel_to_site

# เตือนเรื่องภาษาไทยโดยเฉพาะ — โมเดลภาพชอบทำสระ/วรรณยุกต์หลุดตำแหน่ง
_THAI_WARNING = """\
CRITICAL — THAI TEXT ACCURACY:
The text above is Thai. Reproduce every character exactly as given, including all
vowel marks and tone marks, and keep each mark attached to its correct base
consonant. Do not invent, translate, transliterate or "beautify" any Thai word.
If you cannot render a glyph exactly, leave that line out rather than guessing.\
"""

_NO_TEXT_BLOCK = """\
TEXT:
Render NO text of any kind — no letters, words, numbers, captions or logos.
Leave the left 40% of the frame visually calm and uncluttered (dark gradient,
soft glow only) so that headline text can be composited on top afterwards.\
"""


def _has_thai(text: str) -> bool:
    return any("฀" <= ch <= "๿" for ch in text)


def _wrap(text: str, width: int = 84) -> str:
    """ห่อบรรทัดยาวให้อ่านง่ายตอนพิมพ์ออกหน้าจอ"""
    return "\n".join(textwrap.wrap(" ".join(text.split()), width=width))


def _text_block(lines: list[str], accent_idx: int, theme: style.Theme,
                kicker: str = "", tagline: str = "") -> str:
    out = ["TEXT — render these lines as the headline, flush-left, stacked, "
           "in a heavy condensed sans-serif:"]
    if kicker:
        out.append(f'  KICKER (small, uppercase, letter-spaced, white):  "{kicker}"')
    for i, line in enumerate(lines):
        if i == accent_idx:
            size, colour = "EXTRA LARGE", f"{theme.accent_name} ({theme.accent})"
        else:
            size, colour = "large", "off-white"
        out.append(f'  LINE {i + 1} ({size}, {colour}):  "{line}"')
    out.append(f"  A thin hand-drawn underline stroke in {theme.secondary} sits under "
               f"the {'accent' if len(lines) > 1 else 'headline'} line.")
    if tagline:
        # tagline ของธีม life เป็นภาษาไทย — สั่ง uppercase กับภาษาไทยไม่มีความหมาย
        casing = "small, letter-spaced" if _has_thai(tagline) else "small, uppercase, letter-spaced"
        out.append(f'  BOTTOM-RIGHT TAGLINE ({casing}):  "{tagline}"')
    return "\n".join(out)


def build(post, lines: list[str] | None = None, accent_index: int | None = None,
          kicker: str = "", stats: list[str] | None = None,
          theme: style.Theme | None = None, no_text: bool = False) -> str:
    """ประกอบ prompt เต็มสำหรับโพสต์หนึ่งอัน"""
    theme = theme or style.pick_theme(post)
    lines = lines or style.split_headline(post.headline, post.lang)
    accent_idx = accent_index if accent_index is not None else style.pick_accent_line(lines)

    if no_text:
        text_block = _NO_TEXT_BLOCK
    else:
        text_block = _text_block(lines, accent_idx, theme, kicker, theme.tagline)
        if post.lang == "th":
            text_block += "\n\n" + _THAI_WARNING

    # ประกอบเป็น list แล้ว join — ห้ามใช้ dedent เพราะตัวแปรหลายบรรทัด
    # (HOUSE_STYLE, scene) ชิดซ้ายอยู่แล้ว dedent จะหา common prefix ไม่เจอ
    parts = [
        "Create a blog cover illustration, landscape 3:2 aspect ratio, 1536x1024 pixels.",
        "",
        "STYLE:",
        style.HOUSE_STYLE,
        "",
        f"ACCENT COLOUR: {theme.accent_name} ({theme.accent}), used for the glow, the rim "
        f"light and exactly one headline line. Everything else stays near-black and off-white.",
        "",
        "SCENE:",
        _wrap(theme.scene),
        "",
    ]
    if stats:
        parts += ["BOTTOM STRIP — small icons with these captions:",
                  "  " + "  ·  ".join(stats), ""]
    parts += [text_block, ""]
    return "\n".join(parts)


def render_cli(post, **kwargs) -> str:
    """prompt + คำสั่งว่าจะทำอะไรต่อ — สำหรับพิมพ์ออกหน้าจอ"""
    theme = kwargs.get("theme") or style.pick_theme(post)
    lines = kwargs.get("lines") or style.split_headline(post.headline, post.lang)
    body = build(post, **kwargs)
    bar = "─" * 72

    warn = ""
    too_long = style.long_lines(lines, post.lang)
    if too_long:
        listing = "; ".join(f'"{lines[i]}"' for i in too_long)
        warn = (f"\n\033[33m⚠ บรรทัดยาวเกินจะวางสวย: {listing}\n"
                f"  ตัดเองด้วย --line \"...\" --line \"...\" แล้วสั่งใหม่\033[0m\n")

    return (
        f"\n\033[1m{post.slug}\033[0m  ธีม \033[1m{theme.key}\033[0m "
        f"({theme.accent})  ภาษา {post.lang}\n"
        f"หัวเรื่อง: {post.headline}\n"
        f"{warn}"
        f"\n\033[90m{bar} คัดลอกตั้งแต่บรรทัดถัดไป\033[0m\n"
        f"{body}"
        f"\033[90m{bar} จบ\033[0m\n"
        f"\nเสร็จแล้วบันทึกรูปลง \033[1m{rel_to_site(INCOMING_DIR)}/\033[0m "
        f"แล้วสั่ง \033[1mthumb finish {post.slug}\033[0m\n"
    )
