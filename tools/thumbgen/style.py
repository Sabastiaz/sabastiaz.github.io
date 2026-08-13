"""สไตล์บ้าน Sabastiaz — ถอดจาก thumbnail ที่ทำไว้แล้ว

อ้างอิง: pic/thumb/oscp.jpg, tenablecert.jpg, impostor-mountain.jpg
ไฟล์นี้เป็นแหล่งความจริงเดียวของ "หน้าตา" — ทั้ง prompt.py และโหมด overlay
ดึงค่าจากที่นี่ ไม่มีใครนิยามสีเองซ้ำ
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# DNA ที่เหมือนกันทั้ง 3 ภาพอ้างอิง
HOUSE_STYLE = """\
Cinematic dark digital painting, semi-realistic anime illustration style.
Near-black background with heavy vignette and strong rim lighting in the accent colour.
Composition in three bands:
  LEFT 40%   — the typography block (see TEXT below), stacked flush-left, dominant.
  CENTER 30% — the hero subject, lit from behind, the visual anchor.
  RIGHT 30%  — supporting "evidence" panels: floating UI cards, terminal windows,
               sticky notes or photographs, dimmer than the centre, slightly angled.
A thin horizontal strip across the bottom holds 4-6 small icon + short caption stats.
Bottom-right corner: a small minimal crown glyph next to a one-line tagline.
High contrast, film grain, volumetric light, glowing particles in the accent colour.
No watermark, no signature, no stock-photo look, no border frame.

SAFE AREA — IMPORTANT:
This image is also shown cropped to a wide letterbox that keeps only the middle
60% of its height. Every headline line must sit fully inside the vertical middle
60% of the frame. Keep the top 20% and the bottom 20% for atmosphere only —
background, glow, the stats strip and the tagline. No headline text may touch
either of those bands.\
"""


@dataclass(frozen=True)
class Theme:
    key: str
    accent: str        # สีหลัก
    accent_name: str   # ชื่อสีเป็นคำ — โมเดลภาพเข้าใจคำดีกว่า hex
    secondary: str     # สีรอง ใช้กับบรรทัดเน้นย้ำ/ขีดเส้นใต้
    scene: str         # hero subject + evidence panels ของหมวดนี้
    tagline: str


THEMES: dict[str, Theme] = {
    "offsec": Theme(
        key="offsec",
        accent="#FF6B1A",
        accent_name="burnt orange",
        secondary="#E0483C",
        scene=(
            "Hero: a large glowing hexagonal certification badge floating centre-frame, "
            "with a young male hacker in a dark hoodie standing beside it, seen from behind "
            "or three-quarter back view, face not visible. "
            "Evidence panels: a dark terminal window with green monospace text, a hand-written "
            "checklist card, small sticky notes with short motivational words."
        ),
        tagline="FOCUS. PRACTICE. PERSISTENCE.",
    ),
    "bluecert": Theme(
        key="bluecert",
        accent="#1E90FF",
        accent_name="electric blue",
        secondary="#FFFFFF",
        scene=(
            "Hero: a large glowing hexagonal certification badge floating centre-frame over a "
            "circuit-board glow. "
            "Evidence panels: floating security-dashboard cards with donut charts and trend "
            "lines, a risk table, an email window showing a pass result, a laptop, a trophy."
        ),
        tagline="FIND MORE. FIX SMARTER.",
    ),
    "cert": Theme(
        key="cert",
        accent="#C9A84C",
        accent_name="antique gold",
        secondary="#E0483C",
        scene=(
            "Hero: a large glowing certification emblem centre-frame, framed by faint arcane "
            "geometry. "
            "Evidence panels: a study checklist, a lab topology diagram, a terminal window, "
            "a small stack of books."
        ),
        tagline="ONE MORE SEAL EARNED.",
    ),
    "ctf": Theme(
        key="ctf",
        accent="#39FF14",
        accent_name="neon green",
        secondary="#63D4AF",
        scene=(
            "Hero: a glowing capture-the-flag banner or a cracked digital padlock centre-frame, "
            "streams of falling hex code behind it. "
            "Evidence panels: a terminal with a flag string, a packet-capture window, "
            "a scoreboard card, a puzzle-piece motif."
        ),
        tagline="SOLVE. LEARN. REPEAT.",
    ),
    "pentest": Theme(
        key="pentest",
        accent="#E0563C",
        accent_name="ember red-orange",
        secondary="#FF6B1A",
        scene=(
            "Hero: a compromised server rack or a domain-controller icon centre-frame, glowing "
            "red, with an attack-chain arrow sweeping across it. "
            "Evidence panels: a terminal showing a shell prompt, a network topology graph with "
            "one node highlighted, a privilege-escalation ladder diagram."
        ),
        tagline="ENUMERATE. CHAIN. OWN.",
    ),
    "life": Theme(
        key="life",
        accent="#FFB020",
        accent_name="warm golden amber",
        secondary="#E0483C",
        scene=(
            "Hero: a young man with a backpack seen from behind, looking towards a distant "
            "mountain peak at sunrise, tiny silhouette of a figure standing on the summit. "
            "Evidence panels: a column of dim polaroid-style photographs down the left edge "
            "showing quiet late-night study scenes, each with a small handwritten caption."
        ),
        tagline="เราสร้างภูเขาลูกนี้ขึ้นมาเอง",
    ),
}

DEFAULT_THEME = THEMES["cert"]

# คำในหัวเรื่องที่ชี้ธีมได้แม่นกว่า tag — ตรวจก่อน tag เสมอ
_TITLE_HINTS: list[tuple[str, str]] = [
    (r"\bOSCP\b|\bOSEP\b|\bOSCE\b|OffSec|Offensive Security|PEN-[23]00", "offsec"),
    (r"Tenable|Nessus|Vulnerability Management|Blue Team|SOC\b|Defensive", "bluecert"),
    (r"\bCTF\b|Capture the Flag|Hackloween|Top Talent|WRITE ?UP|Playground", "ctf"),
]

# tag -> ธีม เรียงตามลำดับความสำคัญ (เจออันแรกใช้อันนั้น)
_TAG_PRIORITY: list[tuple[str, str]] = [
    ("cert", "cert"),
    ("ctf", "ctf"),
    ("pentest", "pentest"),
    ("lab", "pentest"),
    ("life", "life"),
]


def pick_theme(post) -> Theme:
    """เลือกธีมจากหัวเรื่อง + tag ของโพสต์"""
    haystack = f"{post.title_en} {post.title_th} {post.og_title} {post.slug}"
    for pattern, key in _TITLE_HINTS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return THEMES[key]

    for tag, key in _TAG_PRIORITY:
        if tag in post.tags:
            return THEMES[key]

    return DEFAULT_THEME


# ── การตัดบรรทัดพาดหัว ────────────────────────────────────────────────
# ภาษาไทยไม่เว้นวรรคระหว่างคำ แต่หัวเรื่องในเว็บนี้เว้นวรรคเป็นวรรคตอนอยู่แล้ว
# เลยตัดที่ space ได้ ส่วนอังกฤษตัดตามจำนวนอักขระ
_SPLIT_MARKS = re.compile(r"\s*[—–:|]\s*|\s+\.\.\.\s*")


def split_headline(text: str, lang: str = "th", max_lines: int = 4) -> list[str]:
    """หั่นหัวเรื่องเป็นบรรทัดสำหรับวางบนภาพ

    เป็นแค่ค่าตั้งต้นที่พออ่านได้ — ควรถูก override ด้วย --line เมื่ออยากได้
    การตัดที่สวยกว่านี้ (ดู SKILL.md)
    """
    text = re.sub(r"\s+", " ", text).strip()
    width = 20 if lang == "th" else 26

    chunks = [c for c in _SPLIT_MARKS.split(text) if c]
    lines: list[str] = []
    for chunk in chunks:
        cur = ""
        for word in chunk.split(" "):
            candidate = f"{cur} {word}".strip()
            if cur and len(candidate) > width:
                lines.append(cur)
                cur = word
            else:
                cur = candidate
        if cur:
            lines.append(cur)

    if len(lines) > max_lines:
        # ยุบส่วนเกินเข้าบรรทัดสุดท้ายแทนที่จะตัดทิ้ง — ห้ามทำหัวเรื่องหาย
        lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :])]
    return lines or [text]


_ACRONYM = re.compile(r"\b[A-Z]{3,}\b")
# แบรนด์/ชื่อเฉพาะที่ควรได้เป็นบรรทัดเด่น ถ้าโผล่ในหัวเรื่อง
_BRAND = re.compile(
    r"\bOSCP\b|\bOSEP\b|\bCPTS\b|\bCRTA\b|\bCAPE\b|Tenable|OffSec|Sliver|"
    r"GodPotato|RustPotato|MSSQL|Hackloween|ChatGPT",
    re.IGNORECASE,
)


def pick_accent_line(lines: list[str]) -> int:
    """บรรทัดไหนควรเป็นสี accent

    ลำดับ: ชื่อแบรนด์ > ตัวย่อพิมพ์ใหญ่ > บรรทัดที่ยาวที่สุด
    """
    for matcher in (_BRAND, _ACRONYM):
        for i, line in enumerate(lines):
            if matcher.search(line):
                return i
    if len(lines) == 1:
        return 0
    return max(range(len(lines)), key=lambda i: len(lines[i]))


def long_lines(lines: list[str], lang: str = "th") -> list[int]:
    """บรรทัดที่ยาวเกินจนวางบนภาพแล้วอ่านยาก

    ภาษาไทยเขียนติดกันไม่มี space — ตัวตัดบรรทัดอัตโนมัติจึงหั่นกลางคำไม่ได้
    เลยได้แต่ชี้ว่าบรรทัดไหนยาวไป ให้คนตัดเองด้วย --line
    """
    limit = 22 if lang == "th" else 30
    return [i for i, line in enumerate(lines) if len(line) > limit]
