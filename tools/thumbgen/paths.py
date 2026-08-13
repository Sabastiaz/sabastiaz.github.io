"""ตำแหน่งไฟล์ต่าง ๆ ในเว็บ — จุดเดียวที่ hardcode path"""
from pathlib import Path

# tools/thumbgen/paths.py -> tools/thumbgen -> tools -> Sabastiaz_Web
SITE_ROOT = Path(__file__).resolve().parents[2]

BLOG_DIR = SITE_ROOT / "blog"
THUMB_DIR = SITE_ROOT / "pic" / "thumb"
INCOMING_DIR = THUMB_DIR / "_incoming"
USED_DIR = INCOMING_DIR / "_used"
WRITINGS = SITE_ROOT / "writings.html"
BACKUP_DIR = SITE_ROOT / "_backup_thumbgen"

# og:image ในโพสต์ใช้ URL absolute ทั้งหมด (ตามของเดิม)
SITE_URL = "https://sabastiaz.github.io"

# ขนาดมาตรฐานของ thumbnail
THUMB_W, THUMB_H = 900, 600
JPEG_QUALITY = 85


def thumb_url(slug: str) -> str:
    return f"{SITE_URL}/pic/thumb/{slug}.jpg"


def thumb_path(slug: str) -> Path:
    return THUMB_DIR / f"{slug}.jpg"


def rel_to_site(p: Path) -> str:
    """path -> string relative ต่อ site root สำหรับพิมพ์ให้อ่านง่าย"""
    try:
        return str(p.relative_to(SITE_ROOT))
    except ValueError:
        return str(p)
