"""ดึงข้อมูลหัวเรื่องออกจากโพสต์บล็อกและการ์ดใน writings.html

อ่านอย่างเดียว — ใช้ bs4 ได้เต็มที่ ไม่กระทบ format ของไฟล์
(การ *เขียน* กลับอยู่ใน wire.py ซึ่งใช้ text surgery แทน)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from paths import BLOG_DIR, WRITINGS, thumb_path


@dataclass
class Post:
    slug: str
    path: Path
    title_en: str = ""
    title_th: str = ""
    og_title: str = ""
    og_desc: str = ""
    og_image: str = ""
    has_twitter_image: bool = False
    tags: list[str] = field(default_factory=list)
    date: str = ""
    read_time: str = ""
    # จากการ์ดใน writings.html
    card_tags: str = ""
    card_title: str = ""
    card_desc: str = ""
    card_thumb: str | None = None       # src ของรูปในการ์ด ถ้ามี
    card_emoji: str | None = None       # emoji placeholder ถ้าการ์ดยังไม่มีรูป
    in_writings: bool = False

    @property
    def lang(self) -> str:
        """'th' ถ้าโพสต์เป็นภาษาไทย ไม่งั้น 'en'"""
        return "th" if "th" in self.tags else "en"

    @property
    def headline(self) -> str:
        """หัวเรื่องที่ควรขึ้นบนภาพ — ใช้ภาษาเดียวกับตัวโพสต์"""
        if self.lang == "th" and self.title_th:
            return self.title_th
        return self.title_en or self.og_title or self.slug

    @property
    def thumb_name(self) -> str | None:
        """ชื่อ thumb (ไม่มีนามสกุล) ที่โพสต์นี้อ้างถึงจริง

        ชื่อไฟล์ไม่ได้ตรงกับ slug เสมอไป — impostor-syndrome-th ใช้
        impostor-mountain.jpg — เลยต้องดูจากสิ่งที่ HTML ชี้ไป ไม่ใช่เดาจาก slug
        """
        for ref in (self.card_thumb or "", self.og_image or ""):
            m = re.search(r"/?pic/thumb/([^/?#]+)\.(?:jpg|jpeg|png|webp)", ref)
            if m:
                return m.group(1)
        return None

    @property
    def has_thumb(self) -> bool:
        name = self.thumb_name
        return bool(name) and thumb_path(name).exists()

    @property
    def target_name(self) -> str:
        """ชื่อไฟล์ที่จะเขียน — ใช้ของเดิมถ้ามี ไม่งั้นใช้ slug"""
        return self.thumb_name or self.slug


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)) if node else ""


def extract_post(post_path: Path) -> Post:
    """อ่านโพสต์ HTML หนึ่งไฟล์"""
    slug = post_path.stem
    soup = BeautifulSoup(post_path.read_text(encoding="utf-8"), "html.parser")
    post = Post(slug=slug, path=post_path)

    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name") or ""
        content = meta.get("content") or ""
        if prop == "og:title":
            post.og_title = content
        elif prop == "og:description":
            post.og_desc = content
        elif prop == "og:image":
            post.og_image = content
        elif prop == "twitter:image":
            post.has_twitter_image = True

    h1 = soup.find("h1", class_="post-title")
    if h1:
        for span in h1.find_all("span", class_="lb"):
            if span.get("lang") == "th":
                post.title_th = _text(span)
            elif span.get("lang") == "en":
                post.title_en = _text(span)
        if not (post.title_en or post.title_th):
            post.title_en = _text(h1)

    tag_box = soup.find("div", class_="post-tags")
    if tag_box:
        for span in tag_box.find_all("span", class_="post-tag"):
            for cls in span.get("class", []):
                # บางโพสต์ติด tag ซ้ำ (brain-body-recover มี life สองครั้ง)
                if cls.startswith("tag-") and cls[4:] not in post.tags:
                    post.tags.append(cls[4:])

    meta_row = soup.find("div", class_="post-meta-row")
    if meta_row:
        parts = [_text(s) for s in meta_row.find_all("span") if "dot" not in (s.get("class") or [])]
        if parts:
            post.date = parts[0]
        if len(parts) > 1:
            post.read_time = parts[1]

    return post


def attach_card(post: Post, writings_html: str | None = None) -> Post:
    """เติมข้อมูลจากการ์ดใน writings.html ลงใน Post (แก้ object เดิม)"""
    html = writings_html if writings_html is not None else WRITINGS.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    card = soup.find("a", class_="tome-card", href=f"blog/{post.slug}.html")
    if not card:
        return post

    post.in_writings = True
    post.card_tags = card.get("data-tags", "")
    post.card_title = _text(card.find("div", class_="tome-title"))
    post.card_desc = _text(card.find("div", class_="tome-desc"))

    thumb = card.find("div", class_="tome-thumb")
    if thumb:
        img = thumb.find("img")
        if img:
            post.card_thumb = img.get("src", "")
        elif "tome-thumb-icon" in (thumb.get("class") or []):
            post.card_emoji = _text(thumb)

    return post


def all_posts(with_cards: bool = True) -> list[Post]:
    """โพสต์ทั้งหมดใน blog/ เรียงตามชื่อไฟล์"""
    posts = [extract_post(p) for p in sorted(BLOG_DIR.glob("*.html"))]
    if with_cards:
        # อ่าน writings.html ครั้งเดียวแล้วใช้ซ้ำ — parse 23 รอบช้าเกินจำเป็น
        html = WRITINGS.read_text(encoding="utf-8")
        for post in posts:
            attach_card(post, html)
    return posts


def load(slug_or_path: str) -> Post:
    """รับได้ทั้ง 'oscp', 'oscp.html', 'blog/oscp.html' หรือ path เต็ม"""
    p = Path(slug_or_path)
    if p.is_absolute() and p.exists():
        post_path = p
    else:
        name = p.name if p.suffix == ".html" else f"{p.name}.html"
        post_path = BLOG_DIR / name
    if not post_path.exists():
        raise FileNotFoundError(f"ไม่พบโพสต์: {post_path}")
    return attach_card(extract_post(post_path))
