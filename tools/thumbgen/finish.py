"""แปลงรูปที่ gen มาจาก ChatGPT ให้เป็น thumbnail มาตรฐานของเว็บ

1536x1024 (3:2) หรือ 1672x941 (16:9) → center-crop 3:2 → 900x600 JPEG
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from paths import (INCOMING_DIR, JPEG_QUALITY, THUMB_DIR, THUMB_H, THUMB_W,
                   USED_DIR, rel_to_site, thumb_path)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
# ไฟล์ที่ทำเสร็จควรอยู่ราว 110-150 KB เท่าของเดิม เกินนี้ค่อยลด quality
MAX_BYTES = 180_000
MIN_QUALITY = 70


@dataclass
class Result:
    source: Path
    dest: Path
    src_size: tuple[int, int]
    src_bytes: int
    out_bytes: int
    quality: int
    cropped: bool
    moved_to: Path | None = None

    def summary(self) -> str:
        w, h = self.src_size
        crop = " (center-crop 3:2)" if self.cropped else ""
        moved = f"\n  ต้นฉบับ  → {rel_to_site(self.moved_to)}" if self.moved_to else ""
        return (
            f"  {rel_to_site(self.source)}\n"
            f"    {w}x{h}  {self.src_bytes / 1_048_576:.1f} MB{crop}\n"
            f"  → {rel_to_site(self.dest)}\n"
            f"    {THUMB_W}x{THUMB_H}  {self.out_bytes / 1024:.0f} KB  (quality {self.quality})"
            f"{moved}"
        )


# การ์ดใน writings.html สูง 140px กว้างราว 340px ใช้ object-fit:cover
# แปลว่ามันโชว์แค่แถบกลางของภาพ ตัดบน/ล่างทิ้งข้างละ ~19%
CARD_W, CARD_H = 340, 140


def card_preview(name: str, dest: Path) -> tuple[Path, float]:
    """เรนเดอร์ว่าภาพนี้จะถูกครอปเหลืออะไรตอนขึ้นการ์ด

    ใช้ตรวจว่าพาดหัวหลุด safe zone ไหม — ปัญหาที่ thumbnail ชุดเก่าเป็นกันหมด
    คืน (path ที่เขียน, สัดส่วนที่ถูกตัดบน/ล่างข้างละเท่าไหร่)
    """
    from PIL import ImageEnhance

    src = thumb_path(name)
    with Image.open(src) as im:
        im = im.convert("RGB")
        scaled_h = round(im.height * CARD_W / im.width)
        im = im.resize((CARD_W, scaled_h), Image.LANCZOS)
        top = (scaled_h - CARD_H) // 2
        im = im.crop((0, top, CARD_W, top + CARD_H))
        # การ์ดมี filter: brightness(.82) saturate(.9) — จำลองให้เหมือนของจริง
        im = ImageEnhance.Brightness(im).enhance(0.82)
        im = ImageEnhance.Color(im).enhance(0.9)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest)
    return dest, top / scaled_h


def newest_incoming() -> Path | None:
    """ไฟล์รูปใหม่ล่าสุดใน _incoming/ (ไม่รวมโฟลเดอร์ _used)"""
    candidates = [
        f for f in INCOMING_DIR.glob("*")
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS and not f.name.startswith(".")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_mtime)


def _crop_to_ratio(img: Image.Image, ratio: float) -> tuple[Image.Image, bool]:
    """ครอบตรงกลางให้ได้สัดส่วนตามต้องการ คืน (ภาพ, ครอปจริงไหม)"""
    w, h = img.size
    current = w / h
    if abs(current - ratio) < 0.01:
        return img, False
    if current > ratio:                    # กว้างเกิน → ตัดซ้ายขวา
        new_w = round(h * ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h)), True
    new_h = round(w / ratio)               # สูงเกิน → ตัดบนล่าง
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h)), True


def _encode(img: Image.Image, dest: Path, dry_run: bool) -> tuple[int, int]:
    """เขียน JPEG โดยไล่ลด quality ถ้าไฟล์ใหญ่เกิน คืน (ขนาดไบต์, quality ที่ใช้)"""
    import io

    quality = JPEG_QUALITY
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        data = buf.getvalue()
        if len(data) <= MAX_BYTES or quality <= MIN_QUALITY:
            break
        quality -= 5

    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return len(data), quality


def run(name: str, source: Path | None = None, dry_run: bool = False,
        keep_source: bool = False) -> Result:
    """ทำ thumbnail หนึ่งใบ

    name   — ชื่อไฟล์ปลายทางโดยไม่มีนามสกุล (ปกติคือ slug ของโพสต์)
    source — ไฟล์ต้นฉบับ ถ้าไม่ระบุจะหยิบไฟล์ใหม่สุดใน _incoming/
    """
    src = source or newest_incoming()
    if src is None:
        raise FileNotFoundError(
            f"ไม่มีรูปใน {rel_to_site(INCOMING_DIR)}/ — วางไฟล์ที่ gen มาลงโฟลเดอร์นี้ก่อน"
        )
    if not src.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์: {src}")

    src_bytes = src.stat().st_size
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)     # กันรูปจากมือถือที่หมุนตาม EXIF
        src_size = im.size
        im, cropped = _crop_to_ratio(im, THUMB_W / THUMB_H)
        im = im.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        if im.mode != "RGB":
            # PNG จาก ChatGPT มี alpha — ทับพื้นดำให้เข้ากับโทนเว็บ ไม่ใช่ขาว
            bg = Image.new("RGB", im.size, (0, 0, 0))
            bg.paste(im, mask=im.split()[-1] if "A" in im.mode else None)
            im = bg

        dest = thumb_path(name)
        out_bytes, quality = _encode(im, dest, dry_run)

    result = Result(
        source=src, dest=dest, src_size=src_size, src_bytes=src_bytes,
        out_bytes=out_bytes, quality=quality, cropped=cropped,
    )

    # ย้ายต้นฉบับออกจากทางเดิน ไม่ให้ค้างเกลื่อนแบบ PNG ชุดเก่า
    if not keep_source and not dry_run and src.parent == INCOMING_DIR:
        USED_DIR.mkdir(parents=True, exist_ok=True)
        target = USED_DIR / src.name
        if target.exists():
            target = USED_DIR / f"{src.stem}-{int(src.stat().st_mtime)}{src.suffix}"
        shutil.move(str(src), str(target))
        result.moved_to = target

    return result
