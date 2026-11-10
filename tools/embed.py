#!/usr/bin/env python3
"""Copy each language's _memory.py into the python block of its PROMPT.md.

Run after editing a script:  python tools/embed.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK = re.compile(r"(```python\n).*?(\n```)", re.S)

for lang in ("en", "ru"):
    script = (ROOT / lang / "_memory.py").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    prompt = ROOT / lang / "PROMPT.md"
    text = prompt.read_text(encoding="utf-8").replace("\r\n", "\n")
    new, count = BLOCK.subn(lambda m: m.group(1) + script + m.group(2), text, count=1)
    if count != 1:
        raise SystemExit(f"{prompt}: python block not found")
    with open(prompt, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print(f"{lang}: {'updated' if new != text else 'already in sync'}")
