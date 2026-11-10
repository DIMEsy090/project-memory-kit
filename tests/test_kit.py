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
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def run(lang, vault, *args):
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / lang / "_memory.py"), "--root", str(vault), *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, result.stdout


def note(vault, rel, body="", front=None, **props):
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    front = front if front is not None else "".join(f"{key}: {value}\n" for key, value in props.items())
    path.write_text((f"---\n{front}---\n" if front else "") + f"# {path.stem}\n{body}\n", encoding="utf-8")


def build(vault, s, broken):
    ideas, decisions, knowledge = s.CARDS
    idea, decision, fact = list(s.STATUSES)
    first = s.STATUSES[idea][0]
    extra = "[[No such card]]" if broken else ""
    note(vault, f"{ideas}Topic/First idea.md",
         f"[[Market|alias]] `[[inside code]]` {extra}\n| a |\n|---|\n| [[Market\\|alias]] |",
         **{s.TYPE: idea, s.STATUS: first, s.SUMMARY: '"Buy shares: exchanges come later"'})
    # type from a multi-line tag list, summary from a line in the text, long body
    note(vault, f"{ideas}Tagged idea.md",
         f"**{s.BODY_LABELS[0]}:** Tagged summary about [[Market|the market]]\n\n" + "words " * 150,
         front=f"tags:\n  - {s.TAG_TYPE}{idea}\n  - topic/x\n{s.STATUS}: {first}\n")
    note(vault, f"{knowledge}Market.md", "![[scheme.png]] [[Old report]] [[split\nlink]]",
         **{s.TYPE: fact, s.STATUS: s.STATUSES[fact][0], s.SUMMARY: "Goods exchange with an order book"})
    # short card without a summary: its name is enough
    note(vault, f"{knowledge}Short note.md", "a few words",
         **{s.TYPE: fact, s.STATUS: s.STATUSES[fact][0]})
    note(vault, f"{decisions}Genre.md",
         **{s.TYPE: decision, s.STATUS: s.STATUSES[decision][0], s.SUMMARY: "Cozy idle manager"})
    (vault / knowledge / "scheme.png").write_bytes(b"")
    note(vault, f"{s.ARCHIVE[0]}Old report.md", "[[dead link inside the archive]]")
    templates = (s.SKIP - {".obsidian", ".git", ".trash"}).pop()
    note(vault, f"{templates}/Idea.md", "[[template link]]")
    if not broken:
        note(vault, s.NOW, "where we stopped")
        return
    note(vault, f"{ideas}Topic/Bad status.md", **{s.TYPE: idea, s.STATUS: "nonsense"})
    note(vault, f"{ideas}No type.md")
    note(vault, f"{ideas}Long without summary.md", "words " * 150, **{s.TYPE: idea, s.STATUS: first})
    note(vault, f"{s.INBOX}Shot.md", **{s.STATUS: s.INBOX_NEW})
    note(vault, f"{knowledge}Sub/Market.md",
         **{s.TYPE: fact, s.STATUS: s.STATUSES[fact][0], s.SUMMARY: "Same name twice"})


for lang in LANGS:
    s = settings(lang)
    script = read(ROOT / lang / "_memory.py")
    embedded = re.search(r"```python\n(.*?)\n```", read(ROOT / lang / "PROMPT.md"), re.S).group(1) + "\n"
    ok(embedded == script, f"{lang}: script inside PROMPT.md differs from _memory.py (run tools/embed.py)")
    first = s.STATUSES[list(s.STATUSES)[0]][0]

    with tempfile.TemporaryDirectory() as tmp:
        vault = pathlib.Path(tmp)
        build(vault, s, broken=False)
        code, out = run(lang, vault, "check")
        ok(code == 0 and s.MSG["result"].format(5, 0) in out, f"{lang}: clean vault should pass\n{out}")
        code, out = run(lang, vault, "list")
        ok(f"[{first}] First idea — Buy shares: exchanges come later" in out, f"{lang}: list line\n{out}")
        ok(f"[{first}] Tagged idea — Tagged summary about the market" in out, f"{lang}: tag type and body summary\n{out}")
        ok(f"] Short note\n" in out, f"{lang}: short card listed without a summary marker\n{out}")
        ok(f"{s.MSG['total']}: 5" in out, f"{lang}: list total\n{out}")
        code, out = run(lang, vault, "list", s.CARDS[0], "--status", first)
        ok(f"{s.MSG['total']}: 2" in out, f"{lang}: list by folder and status\n{out}")
        code, out = run(lang, vault, "list", "--find", "order book")
        ok(f"{s.MSG['total']}: 1" in out and "Market" in out, f"{lang}: list --find by summary\n{out}")
        code, out = run(lang, vault, "list", "--find", "tagged summary")
        ok(f"{s.MSG['total']}: 1" in out, f"{lang}: list --find by body summary\n{out}")

    with tempfile.TemporaryDirectory() as tmp:
        vault = pathlib.Path(tmp)
        build(vault, s, broken=True)
        code, out = run(lang, vault, "check")
        ok(code == 1 and s.MSG["result"].format(9, 7) in out, f"{lang}: broken vault should report 7 issues\n{out}")
        for key in ("type", "status", "summary", "inbox", "link", "dup", "now_missing"):
            ok(s.MSG[key] in out, f"{lang}: message «{key}» missing\n{out}")
        ok("Long without summary" in out and "Short note" not in out, f"{lang}: only long cards need a summary\n{out}")
        ok("inside code" not in out and "inside the archive" not in out and "template link" not in out
           and "split" not in out, f"{lang}: links in code, Archive, Templates and across lines must be ignored\n{out}")

en, ru = (read(ROOT / lang / "_memory.py") for lang in LANGS)
ok(en.split(MARK)[1] == ru.split(MARK)[1], "logic differs between en and ru scripts")
ok(set(settings("en").MSG) == set(settings("ru").MSG), "MSG keys differ between en and ru")
print(f"ok: {checks} checks")
