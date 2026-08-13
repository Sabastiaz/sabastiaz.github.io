"""สำรวจสถานะ thumbnail ของทั้งเว็บ — ไม่แก้อะไรทั้งสิ้น"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import extract
from paths import SITE_ROOT, THUMB_DIR, rel_to_site


@dataclass
class Report:
    posts: list = field(default_factory=list)
    missing: list = field(default_factory=list)      # ยังไม่มีรูป — ต้อง gen ใหม่
    broken: list = field(default_factory=list)       # ชี้ไฟล์ที่ถูกลบไปแล้ว = 404 บนเว็บสด
    emoji_card: list = field(default_factory=list)   # การ์ดยังเป็น emoji
    oversized_og: list = field(default_factory=list) # og:image ชี้ PNG ใหญ่นอก thumb/
    no_twitter: list = field(default_factory=list)   # ไม่มี twitter:image
    no_card: list = field(default_factory=list)      # ไม่มีการ์ดใน writings.html
    orphans: list = field(default_factory=list)      # ไฟล์ใน thumb/ ที่ไม่มีใครอ้าง


def _file_size_mb(name: str) -> float:
    p = SITE_ROOT / name.lstrip("/")
    return p.stat().st_size / 1_048_576 if p.exists() else 0.0


def _referenced_thumb_files() -> set[str]:
    """ชื่อไฟล์ใน pic/thumb/ ที่ถูกอ้างถึงจาก HTML ไฟล์ไหนก็ได้ทั้งเว็บ

    สแกนจาก text ดิบ ไม่ผูกกับ Post เพราะการ์ดบางใบใน writings.html
    ลิงก์ออก Medium ไม่ได้ชี้ blog/*.html แต่ก็ยังใช้รูปใน thumb/ อยู่
    """
    names: set[str] = set()
    html_files = [p for p in SITE_ROOT.glob("*.html")]
    html_files += list((SITE_ROOT / "blog").glob("*.html"))
    for f in html_files:
        for m in re.finditer(r"pic/thumb/([^\"'\s>?#]+)", f.read_text(encoding="utf-8")):
            names.add(m.group(1))
    return names


def run() -> Report:
    rep = Report(posts=extract.all_posts())
    referenced = _referenced_thumb_files()

    for post in rep.posts:
        if not post.has_thumb:
            rep.missing.append(post)
            # อ้างชื่อไฟล์ไว้แต่ไฟล์หายไป — ต่างจาก "ไม่เคยมีรูป" เพราะอันนี้
            # ทำให้เว็บที่ออนไลน์อยู่แสดงรูปแตกทันที ต้องรีบกว่า
            if post.thumb_name:
                rep.broken.append((post, f"pic/thumb/{post.thumb_name}.jpg"))
        if post.card_emoji:
            rep.emoji_card.append(post)
        if not post.in_writings:
            rep.no_card.append(post)
        if not post.has_twitter_image:
            rep.no_twitter.append(post)

        # og:image ที่ยังชี้ไฟล์ต้นฉบับใน pic/ แทน pic/thumb/
        if post.og_image and "/pic/thumb/" not in post.og_image:
            rel = post.og_image.split("sabastiaz.github.io/", 1)[-1]
            rep.oversized_og.append((post, rel, _file_size_mb(rel)))

    for f in sorted(THUMB_DIR.glob("*")):
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            if f.name not in referenced:
                rep.orphans.append((f, f.stat().st_size / 1_048_576))

    return rep


def print_report(rep: Report) -> None:
    print(f"\n\033[1mโพสต์ทั้งหมด {len(rep.posts)} — มี thumbnail แล้ว "
          f"{len(rep.posts) - len(rep.missing)}, ขาด {len(rep.missing)}\033[0m")

    if rep.broken:
        print(f"\n\033[31m▸ รูปแตกบนเว็บสด — HTML ชี้ไฟล์ที่ไม่มีแล้ว ({len(rep.broken)})\033[0m")
        for p, ref in rep.broken:
            hint = ""
            for ext in (".png", ".jpeg", ".webp"):
                alt = THUMB_DIR / (Path(ref).stem + ext)
                if alt.exists():
                    hint = (f"  ← มี {alt.name} อยู่ ใช้: "
                            f"thumb finish {p.slug} --source pic/thumb/{alt.name}")
                    break
            print(f"    {p.slug:<24} → {ref} (ไม่มีไฟล์){hint}")

    if rep.missing:
        print(f"\n\033[33m▸ ยังไม่มี thumbnail ({len(rep.missing)})\033[0m")
        for p in rep.missing:
            mark = f"  การ์ด: {p.card_emoji}" if p.card_emoji else ""
            print(f"    {p.slug:<24} [{p.lang}] {p.headline[:52]}{mark}")

    if rep.oversized_og:
        total = sum(mb for _, _, mb in rep.oversized_og)
        print(f"\n\033[33m▸ og:image ยังชี้ไฟล์นอก pic/thumb/ ({len(rep.oversized_og)}, "
              f"รวม {total:.1f} MB)\033[0m")
        for p, rel, mb in rep.oversized_og:
            print(f"    {p.slug:<24} → {rel}  ({mb:.1f} MB)")

    if rep.no_twitter:
        print(f"\n\033[33m▸ ไม่มี twitter:image ({len(rep.no_twitter)})\033[0m")
        print(f"    {', '.join(p.slug for p in rep.no_twitter)}")

    if rep.no_card:
        print(f"\n\033[33m▸ ไม่มีการ์ดใน writings.html ({len(rep.no_card)})\033[0m")
        print(f"    {', '.join(p.slug for p in rep.no_card)}")

    if rep.orphans:
        total = sum(mb for _, mb in rep.orphans)
        print(f"\n\033[90m▸ ไฟล์ใน pic/thumb/ ที่ไม่มีใครอ้างถึง ({len(rep.orphans)}, "
              f"รวม {total:.1f} MB)\033[0m")
        for f, mb in rep.orphans:
            print(f"    {rel_to_site(f):<40} {mb:>6.1f} MB")

    print()
