#!/usr/bin/env python3
"""thumbgen — workflow สร้าง thumbnail จากหัวเรื่องบล็อก

  thumb scan                        ดูว่าโพสต์ไหนยังขาดรูป
  thumb prompt <slug>               ปั้น prompt ไปวางใน ChatGPT
  thumb finish <slug>               ย่อรูปใน _incoming/ แล้วเชื่อมเข้าเว็บ
  thumb wire <slug>                 เชื่อม HTML อย่างเดียว (ไม่แตะรูป)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extract          # noqa: E402
import finish           # noqa: E402
import prompt as prompt_mod  # noqa: E402
import scan as scan_mod      # noqa: E402
import style            # noqa: E402
import wire as wire_mod      # noqa: E402
from paths import INCOMING_DIR, rel_to_site  # noqa: E402


def cmd_scan(args) -> int:
    scan_mod.print_report(scan_mod.run())
    return 0


def cmd_prompt(args) -> int:
    post = extract.load(args.slug)
    theme = style.THEMES[args.theme] if args.theme else None
    print(prompt_mod.render_cli(
        post,
        lines=args.line or None,
        accent_index=args.accent,
        kicker=args.kicker or "",
        stats=args.stat or None,
        theme=theme,
        no_text=args.no_text,
    ))
    return 0


def cmd_finish(args) -> int:
    post = extract.load(args.slug)
    name = args.name or post.target_name
    source = Path(args.source).expanduser().resolve() if args.source else None

    try:
        result = finish.run(name, source=source, dry_run=args.dry_run,
                            keep_source=args.keep_source)
    except FileNotFoundError as e:
        print(f"\033[31m✗ {e}\033[0m")
        return 1

    print(f"\n\033[1m{post.slug}\033[0m")
    print(result.summary())

    if args.no_wire:
        print("\n\033[90m(ข้าม --no-wire: ยังไม่ได้แก้ HTML)\033[0m")
        return 0

    print()
    try:
        for line in wire_mod.wire(post, name, dry_run=args.dry_run, force=args.dry_run):
            print(line)
    except FileNotFoundError as e:
        print(f"\033[31m✗ {e}\033[0m")
        return 1
    return 0


def cmd_wire(args) -> int:
    post = extract.load(args.slug)
    try:
        for line in wire_mod.wire(post, args.name, dry_run=args.dry_run, force=args.force):
            print(line)
    except FileNotFoundError as e:
        print(f"\033[31m✗ {e}\033[0m")
        return 1
    return 0


def cmd_preview(args) -> int:
    """เรนเดอร์ว่ารูปจะถูกครอปเหลืออะไรตอนขึ้นการ์ดใน writings.html"""
    post = extract.load(args.slug)
    name = args.name or post.target_name
    dest = Path(args.out) if args.out else Path(f"/tmp/thumb-preview-{name}.png")
    try:
        dest, ratio = finish.card_preview(name, dest)
    except FileNotFoundError:
        print(f"\033[31m✗ ยังไม่มีไฟล์ pic/thumb/{name}.jpg\033[0m")
        return 1
    print(f"\nการ์ดจะโชว์แค่แถบกลาง — ตัดบน/ล่างข้างละ {ratio * 100:.0f}%")
    print(f"เปิดดู: {dest}")
    print("ถ้าพาดหัวโดนตัดหัวหรือท้าย แปลว่าภาพวางตัวอักษรสูง/ต่ำเกิน ต้อง gen ใหม่\n")
    return 0


def cmd_incoming(args) -> int:
    """ดูว่ามีอะไรรออยู่ในโฟลเดอร์ drop บ้าง"""
    files = sorted(INCOMING_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True) \
        if INCOMING_DIR.exists() else []
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]
    if not files:
        print(f"ไม่มีไฟล์รอใน {rel_to_site(INCOMING_DIR)}/")
        return 0
    print(f"\nไฟล์รออยู่ใน {rel_to_site(INCOMING_DIR)}/ ({len(files)}):")
    for f in files:
        print(f"  {f.name:<44} {f.stat().st_size / 1_048_576:>5.1f} MB")
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="thumb", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scan", help="โพสต์ไหนยังขาด thumbnail")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("prompt", help="ปั้น prompt สำหรับ ChatGPT")
    sp.add_argument("slug")
    sp.add_argument("--line", action="append", metavar="TEXT",
                    help="กำหนดบรรทัดพาดหัวเอง ใส่ซ้ำได้หลายครั้ง")
    sp.add_argument("--accent", type=int, metavar="N",
                    help="บรรทัดที่ N (เริ่มจาก 0) ให้เป็นสี accent")
    sp.add_argument("--kicker", help="ข้อความเล็กเหนือพาดหัว")
    sp.add_argument("--stat", action="append", metavar="TEXT",
                    help="ตัวเลขในแถบล่าง ใส่ซ้ำได้")
    sp.add_argument("--theme", choices=sorted(style.THEMES), help="บังคับธีมสี")
    sp.add_argument("--no-text", action="store_true",
                    help="ขอภาพพื้นหลังเปล่า ไม่มีตัวอักษร (ไว้ overlay เอง)")
    sp.set_defaults(func=cmd_prompt)

    sp = sub.add_parser("finish", help="ย่อรูป + เชื่อมเข้าเว็บ")
    sp.add_argument("slug")
    sp.add_argument("--source", help="ไฟล์ต้นฉบับ (ไม่ระบุ = ไฟล์ใหม่สุดใน _incoming/)")
    sp.add_argument("--name", help="ชื่อไฟล์ปลายทาง (ไม่ระบุ = ใช้ของเดิมหรือ slug)")
    sp.add_argument("--dry-run", action="store_true", help="ดูผลโดยไม่เขียนอะไร")
    sp.add_argument("--keep-source", action="store_true", help="ไม่ต้องย้ายต้นฉบับไป _used/")
    sp.add_argument("--no-wire", action="store_true", help="ทำแค่รูป ไม่แตะ HTML")
    sp.set_defaults(func=cmd_finish)

    sp = sub.add_parser("wire", help="แก้ og:image/twitter:image + การ์ด")
    sp.add_argument("slug")
    sp.add_argument("--name", help="ชื่อไฟล์ thumbnail ที่จะชี้ไป")
    sp.add_argument("--dry-run", action="store_true", help="แสดง diff โดยไม่เขียน")
    sp.add_argument("--force", action="store_true", help="ยอมชี้ไฟล์ที่ยังไม่มี")
    sp.set_defaults(func=cmd_wire)

    sp = sub.add_parser("preview", help="ดูว่ารูปจะถูกครอปเหลืออะไรตอนขึ้นการ์ด")
    sp.add_argument("slug")
    sp.add_argument("--name", help="ชื่อไฟล์ thumbnail")
    sp.add_argument("--out", help="ที่เก็บไฟล์ preview")
    sp.set_defaults(func=cmd_preview)

    sp = sub.add_parser("incoming", help="ดูไฟล์ที่รออยู่ในโฟลเดอร์ drop")
    sp.set_defaults(func=cmd_incoming)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
