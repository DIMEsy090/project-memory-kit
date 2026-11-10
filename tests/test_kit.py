#!/usr/bin/env python3
"""Checks for the kit. Run:  python tests/test_kit.py

For each language: builds a clean and a broken sample vault, runs the script on
both, and checks that the script inside PROMPT.md is the same as _memory.py.
"""
import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "# ---- logic: identical in every language version ----"
LANGS = ("en", "ru")
checks = 0


def ok(condition, what):
    global checks
    if not condition:
        raise SystemExit(f"FAIL: {what}")
    checks += 1


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def settings(lang):
    spec = importlib.util.spec_from_file_location(f"memory_{lang}", ROOT / lang / "_memory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(lang, vault, *args):
    result = subprocess.run(
        [sys.executable, str(ROOT / lang / "_memory.py"), "--root", str(vault), *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, result.stdout


def note(vault, rel, body="", **props):
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    front = "".join(f"{key}: {value}\n" for key, value in props.items())
    path.write_text((f"---\n{front}---\n" if props else "") + f"# {path.stem}\n{body}\n", encoding="utf-8")


def build(vault, s, broken):
    ideas, decisions, knowledge = s.CARDS
    idea, decision, fact = list(s.STATUSES)
    extra = "[[No such card]]" if broken else ""
    note(vault, f"{ideas}Topic/First idea.md",
         f"[[Market|alias]] `[[inside code]]` {extra}\n| a |\n|---|\n| [[Market\\|alias]] |",
         **{s.TYPE: idea, s.STATUS: s.STATUSES[idea][0], s.SUMMARY: '"Buy shares: exchanges come later"'})
    note(vault, f"{knowledge}Market.md", "![[scheme.png]] [[Old report]]",
         **{s.TYPE: fact, s.STATUS: s.STATUSES[fact][0], s.SUMMARY: "Goods exchange with an order book"})
    note(vault, f"{decisions}Genre.md",
         **{s.TYPE: decision, s.STATUS: s.STATUSES[decision][0], s.SUMMARY: "Cozy idle manager"})
    (vault / knowledge / "scheme.png").write_bytes(b"")
    note(vault, f"{s.ARCHIVE}Old report.md", "[[dead link inside the archive]]")
    templates = (s.SKIP - {".obsidian", ".git", ".trash"}).pop()
    note(vault, f"{templates}/Idea.md", "[[template link]]")
    if not broken:
        note(vault, s.NOW, "where we stopped")
        return
    note(vault, f"{ideas}Topic/Bad status.md", **{s.TYPE: idea, s.STATUS: "nonsense"})
    note(vault, f"{ideas}No type.md")
    note(vault, f"{s.INBOX}Shot.md", **{s.STATUS: s.INBOX_NEW})
    note(vault, f"{knowledge}Sub/Market.md",
         **{s.TYPE: fact, s.STATUS: s.STATUSES[fact][0], s.SUMMARY: "Same name twice"})


for lang in LANGS:
    s = settings(lang)
    script = read(ROOT / lang / "_memory.py")
    embedded = re.search(r"```python\n(.*?)\n```", read(ROOT / lang / "PROMPT.md"), re.S).group(1) + "\n"
    ok(embedded == script, f"{lang}: script inside PROMPT.md differs from _memory.py (run tools/embed.py)")

    with tempfile.TemporaryDirectory() as tmp:
        vault = pathlib.Path(tmp)
        build(vault, s, broken=False)
        code, out = run(lang, vault, "check")
        ok(code == 0 and s.MSG["result"].format(3, 0) in out, f"{lang}: clean vault should pass\n{out}")
        code, out = run(lang, vault, "list")
        first = s.STATUSES[list(s.STATUSES)[0]][0]
        ok(f"[{first}] First idea — Buy shares: exchanges come later" in out, f"{lang}: list line\n{out}")
        ok(f"{s.MSG['total']}: 3" in out, f"{lang}: list total\n{out}")
        code, out = run(lang, vault, "list", s.CARDS[0], "--status", first)
        ok(f"{s.MSG['total']}: 1" in out, f"{lang}: list by folder and status\n{out}")
        code, out = run(lang, vault, "list", "--find", "order book")
        ok(f"{s.MSG['total']}: 1" in out and "Market" in out, f"{lang}: list --find\n{out}")

    with tempfile.TemporaryDirectory() as tmp:
        vault = pathlib.Path(tmp)
        build(vault, s, broken=True)
        code, out = run(lang, vault, "check")
        ok(code == 1 and s.MSG["result"].format(6, 8) in out, f"{lang}: broken vault should report 8 issues\n{out}")
        for key in ("type", "status", "summary", "inbox", "link", "dup", "now_missing"):
            ok(s.MSG[key] in out, f"{lang}: message «{key}» missing\n{out}")
        ok("inside code" not in out and "inside the archive" not in out and "template link" not in out,
           f"{lang}: links in code, Archive and Templates must be ignored\n{out}")

en, ru = (read(ROOT / lang / "_memory.py") for lang in LANGS)
ok(en.split(MARK)[1] == ru.split(MARK)[1], "logic differs between en and ru scripts")
ok(set(settings("en").MSG) == set(settings("ru").MSG), "MSG keys differ between en and ru")
print(f"ok: {checks} checks")
