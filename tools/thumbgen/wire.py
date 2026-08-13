"""เชื่อม thumbnail เข้ากับ HTML — og:image, twitter:image และการ์ดใน writings.html

แก้ไฟล์แบบ text surgery ทีละบรรทัด ไม่ใช้ bs4 เขียนกลับ เพราะ bs4 จะ
จัดรูปแบบทั้งไฟล์ใหม่ (writings.html เขียนมือเว้นวรรคสวย ๆ ไว้ จะพังหมด)
ทุกฟังก์ชันต้อง idempotent — รันซ้ำแล้วไฟล์ต้องไม่เปลี่ยน
"""
from __future__ import annotations

import difflib
import html
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from paths import BACKUP_DIR, WRITINGS, rel_to_site, thumb_path, thumb_url

_OG_IMAGE = re.compile(r'^(\s*)<meta\s+content="([^"]*)"\s+property="og:image"\s*/?>', re.I)
_TWITTER_IMAGE = re.compile(r'property="twitter:image"|name="twitter:image"', re.I)


@dataclass
class Change:
    path: Path
    before: str
    after: str
    notes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def diff(self) -> str:
        return "".join(difflib.unified_diff(
            self.before.splitlines(keepends=True),
            self.after.splitlines(keepends=True),
            fromfile=f"a/{rel_to_site(self.path)}",
            tofile=f"b/{rel_to_site(self.path)}",
            n=1,
        ))


def _backup(path: Path) -> Path:
    """สำเนาไฟล์ก่อนเขียนทับ — เว็บนี้ไม่ใช่ git repo ไม่มี undo อย่างอื่น"""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / stamp / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def patch_post(post, name: str | None = None) -> Change:
    """ตั้ง og:image ให้ชี้ thumbnail และเพิ่ม twitter:image ถ้ายังไม่มี"""
    name = name or post.target_name
    url = thumb_url(name)
    text = post.path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    notes: list[str] = []

    has_twitter = any(_TWITTER_IMAGE.search(ln) for ln in lines)
    og_idx = None

    for i, line in enumerate(lines):
        m = _OG_IMAGE.match(line)
        if m:
            og_idx = i
            indent, current = m.group(1), m.group(2)
            if current != url:
                lines[i] = f'{indent}<meta content="{url}" property="og:image"/>\n'
                notes.append(f"og:image  {current.split('/')[-1]} → {name}.jpg")
            break

    if og_idx is None:
        notes.append("⚠ ไม่พบ og:image ในไฟล์นี้ — ข้าม")
    elif not has_twitter:
        # วางต่อจาก og:image ให้ meta ของโซเชียลอยู่ติดกัน
        indent = _OG_IMAGE.match(lines[og_idx]).group(1)
        lines.insert(og_idx + 1, f'{indent}<meta content="{url}" name="twitter:image"/>\n')
        notes.append("เพิ่ม twitter:image")

    return Change(post.path, text, "".join(lines), notes)


def patch_card(post, name: str | None = None, writings_text: str | None = None) -> Change:
    """แทนที่ tome-thumb ในการ์ดของโพสต์นี้ด้วย <img> ที่ชี้ thumbnail"""
    name = name or post.target_name
    text = writings_text if writings_text is not None else WRITINGS.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    notes: list[str] = []

    alt = html.escape(post.card_title or post.headline, quote=True)
    href = f'href="blog/{post.slug}.html"'

    start = next((i for i, ln in enumerate(lines) if href in ln), None)
    if start is None:
        notes.append(f"⚠ ไม่พบการ์ดของ {post.slug} ใน writings.html — ข้าม")
        return Change(WRITINGS, text, text, notes)

    # หา tome-thumb ภายในการ์ดใบนี้เท่านั้น หยุดเมื่อเจอ </a> ปิดการ์ด
    for i in range(start, min(start + 20, len(lines))):
        if "</a>" in lines[i]:
            notes.append(f"⚠ การ์ด {post.slug} ไม่มี div.tome-thumb — ข้าม")
            break
        if "tome-thumb" in lines[i]:
            indent = re.match(r"\s*", lines[i]).group(0)
            new = (f'{indent}<div class="tome-thumb">'
                   f'<img src="pic/thumb/{name}.jpg" alt="{alt}" loading="lazy"></div>\n')
            if lines[i] != new:
                old = lines[i].strip()
                was = "emoji placeholder" if "tome-thumb-icon" in old else "รูปเดิม"
                notes.append(f"การ์ด writings.html: {was} → {name}.jpg")
                lines[i] = new
            break

    return Change(WRITINGS, text, "".join(lines), notes)


def apply(changes: list[Change], dry_run: bool = False) -> list[str]:
    """เขียนการเปลี่ยนแปลงลงดิสก์ (หรือแค่รายงานถ้า dry_run) คืนสรุปเป็นบรรทัด"""
    out: list[str] = []
    for ch in changes:
        for note in ch.notes:
            out.append(f"  {note}")
        if not ch.changed:
            out.append(f"  \033[90m{rel_to_site(ch.path)} — ไม่มีอะไรต้องแก้\033[0m")
            continue
        if dry_run:
            out.append(f"\033[90m{ch.diff()}\033[0m")
        else:
            backup = _backup(ch.path)
            ch.path.write_text(ch.after, encoding="utf-8")
            out.append(f"  \033[32m✓\033[0m เขียน {rel_to_site(ch.path)} "
                       f"\033[90m(สำรอง {rel_to_site(backup)})\033[0m")
    return out


def wire(post, name: str | None = None, dry_run: bool = False,
         force: bool = False) -> list[str]:
    """เชื่อมครบทั้งโพสต์และการ์ดในคราวเดียว

    ปฏิเสธถ้าไฟล์รูปยังไม่มีจริง — ไม่งั้นจะเขียน og:image ชี้ 404 ลงเว็บสด
    """
    name = name or post.target_name
    target = thumb_path(name)
    if not target.exists() and not force:
        raise FileNotFoundError(
            f"ยังไม่มีไฟล์ {rel_to_site(target)} — สร้างรูปก่อนด้วย 'thumb finish {post.slug}'\n"
            f"(ถ้าจงใจจะเขียนล่วงหน้าจริง ๆ ใช้ --force)"
        )
    return apply([patch_post(post, name), patch_card(post, name)], dry_run=dry_run)
