#!/usr/bin/env python3
"""PostToolUse hook — โพสต์ใหม่ถูกเขียนลง blog/ เมื่อไหร่ ให้เด้ง prompt ออกมาทันที

กติกาเหล็ก: hook นี้ต้อง **เงียบและ exit 0** ทุกกรณีที่ไม่เกี่ยวข้อง
ถ้ามันพัง มันจะไปขวางการแก้ไฟล์อื่นทั้งเว็บ — เลย try/except คลุมทั้งหมด
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MAX_CONTEXT = 9_500   # เพดานจริงของ additionalContext คือ 10,000 อักขระ


def _silent() -> None:
    sys.exit(0)


def _emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text[:MAX_CONTEXT],
        }
    }))
    sys.exit(0)


def _target_path(payload: dict) -> Path | None:
    """ดึง path ของไฟล์ที่เพิ่งถูกเขียน — ชื่อ field ต่างกันตามเวอร์ชัน เลยลองหลายชื่อ"""
    out = payload.get("tool_output") or {}
    inp = payload.get("tool_input") or {}
    for source in (out, inp):
        if not isinstance(source, dict):
            continue
        for key in ("file_path", "path", "filePath"):
            value = source.get(key)
            if isinstance(value, str) and value:
                return Path(value)
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _silent()

    if payload.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        _silent()

    target = _target_path(payload)
    if target is None:
        _silent()

    try:
        from paths import BLOG_DIR

        target = target.resolve()
        if target.suffix.lower() != ".html" or target.parent != BLOG_DIR.resolve():
            _silent()

        import extract
        import prompt as prompt_mod
        import style

        post = extract.load(str(target))
        if post.has_thumb:
            _silent()

        lines = style.split_headline(post.headline, post.lang)
        theme = style.pick_theme(post)
        too_long = style.long_lines(lines, post.lang)

        note = ""
        if too_long:
            note = (
                "\n⚠ การตัดบรรทัดด้านล่างเป็นค่าตั้งต้นที่หั่นตาม space เท่านั้น "
                "ซึ่งใช้กับภาษาไทยไม่ได้ — ให้ตัดบรรทัดใหม่เองตามความหมาย "
                "แล้วรันคำสั่งข้างล่างพร้อม --line ก่อนส่ง prompt ให้ผู้ใช้\n"
            )

        _emit(
            f"[thumbgen] โพสต์ '{post.slug}' ยังไม่มี thumbnail\n"
            f"หัวเรื่อง: {post.headline}\n"
            f"ภาษา: {post.lang}   ธีมที่เดาได้: {theme.key} ({theme.accent})\n"
            f"{note}\n"
            f"ขั้นถัดไป — ใช้ skill /thumb หรือรันตรง ๆ:\n"
            f"    python3 tools/thumbgen/cli.py prompt {post.slug} \\\n"
            f"      --line \"...\" --line \"...\" --accent N\n\n"
            f"แล้วส่ง prompt ที่ได้ให้ผู้ใช้เอาไปวางใน ChatGPT, ให้เขาลากรูปลง "
            f"pic/thumb/_incoming/, จากนั้นสั่ง "
            f"'python3 tools/thumbgen/cli.py finish {post.slug}'\n"
        )
    except SystemExit:
        raise
    except Exception:
        # hook ห้ามทำให้ flow หลักสะดุด — เงียบไว้ดีกว่าโวยวาย
        _silent()


if __name__ == "__main__":
    main()
