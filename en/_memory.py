#!/usr/bin/env python3
# Project memory: card list and vault check. Lives in the vault root, no dependencies.
USAGE = """python _memory.py list [folder] [--status status] [--find word]   one line per card: [status] name — summary
python _memory.py check                                          vault check; exit code 1 if anything is found"""
CARDS = ("Ideas/", "Decisions/", "Knowledge/")  # folders that hold cards
ARCHIVE = ("Archive/",)  # folders and files that are not checked; add your own
INBOX, NOW = "Inbox/", "Now.md"
SKIP = {".obsidian", ".git", ".trash", "Templates"}
TYPE, STATUS, SUMMARY = "type", "status", "summary"
TAG_TYPE = "type/"  # the type can also be a tag: tags: [type/idea]
BODY_LABELS = ("Summary", "What", "Who")  # the summary can also be a "**Summary:** …" line in the text
SHORT = 700  # a shorter card is described by its name and needs no summary
GENERATED = ()  # folders a script writes from code: no summary required there
NOT_CARDS = set()  # types of index or service notes inside card folders, e.g. {"process"}
STATUSES = {
    "idea": ["new", "decided", "in progress", "done", "postponed", "rejected", "replaced"],
    "decision": ["active", "replaced"],
    "knowledge": ["current", "draft", "outdated"],
}
INBOX_NEW = "new"
MSG = {
    "empty": "(no summary)",
    "total": "total",
    "type": "missing or unknown `type`",
    "status": "status not in the dictionary",
    "summary": "long card without a `summary`",
    "long": "`summary` longer than 160 characters",
    "big": "card over 6000 characters: split it or move the details to Archive",
    "inbox": "inbox item not processed",
    "link": "link to nowhere",
    "dup": "duplicate note names",
    "now_missing": "file is missing",
    "now_stale": "not updated for {} days",
    "now_long": "{} lines, keep it under 40",
    "more": "… and {} more",
    "result": "cards: {}, issues: {}",
}
# ---- logic: identical in every language version ----
import collections
import os
import re
import sys
import time

ARGS = sys.argv[1:]


def opt(name):
    if name in ARGS:
        i = ARGS.index(name)
        value = ARGS[i + 1]
        del ARGS[i:i + 2]
        return value


ROOT = os.path.abspath(opt("--root") or os.path.dirname(os.path.abspath(__file__)))
FM = re.compile(r"\A\ufeff?---\r?\n(.*?)\r?\n---", re.S)
KEY = re.compile(r"^([^\s:#-][^:\n]*):[ \t]*(.*)$", re.M)
TAGTYPE = re.compile(re.escape(TAG_TYPE) + r"([^\s,\]\"']+)")
BODYSUM = re.compile(r"^\*\*(?:" + "|".join(map(re.escape, BODY_LABELS)) + r"):\*\*[ \t]*(.+)$", re.M)
LINK = re.compile(r"\[\[([^\]|#\n]+)(?:[|#][^\]\n]*)?\]\]")
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)


def load():
    notes, targets = [], set()
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            stem, ext = os.path.splitext(f)
            path = os.path.join(folder, f)
            targets.add(stem if ext == ".md" else f)
            if ext == ".md":
                text = open(path, encoding="utf-8", errors="replace").read()
                m = FM.match(text)
                fm = {k.strip(): v.strip().strip("\"'") for k, v in KEY.findall(m.group(1))} if m else {}
                if m and not fm.get(TYPE):
                    tag = TAGTYPE.search(m.group(1))
                    if tag:
                        fm[TYPE] = tag.group(1)
                notes.append((os.path.relpath(path, ROOT).replace(os.sep, "/"), stem, fm, text))
    return sorted(notes), targets


def summary_of(fm, text):
    s = fm.get(SUMMARY, "")
    if not s:
        m = BODYSUM.search(text)
        if m:
            s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", m.group(1)).replace("**", "").strip()
            s = s if len(s) <= 150 else s[:147].rstrip() + "…"
    return s


def self_described(rel, text):
    return rel.startswith(GENERATED) or len(FM.sub("", text, count=1)) <= SHORT


def is_card(rel, fm):
    return rel.startswith(CARDS) and not rel.startswith(ARCHIVE) and fm.get(TYPE) not in NOT_CARDS


def cmd_list():
    status, find = opt("--status"), (opt("--find") or "").lower()
    where = (ARGS[1].strip("/") + "/") if len(ARGS) > 1 else CARDS
    notes, _ = load()
    head, n = None, 0
    for rel, stem, fm, text in notes:
        if not rel.startswith(where) or not is_card(rel, fm):
            continue
        if status and fm.get(STATUS) != status:
            continue
        summary = summary_of(fm, text)
        if find and find not in f"{stem} {summary} {fm.get('tags', '')}".lower():
            continue
        folder = rel.rsplit("/", 1)[0]
        if folder != head:
            head = folder
            print(f"\n# {folder}")
        tail = f" — {summary}" if summary else ("" if self_described(rel, text) else f" — {MSG['empty']}")
        print(f"[{fm.get(STATUS) or '?'}] {stem}{tail}")
        n += 1
    print(f"\n{MSG['total']}: {n}")


def cmd_check():
    notes, targets = load()
    found = collections.OrderedDict()

    def bad(kind, item):
        found.setdefault(kind, []).append(item)

    for rel, stem, fm, text in notes:
        if rel.startswith(ARCHIVE):
            continue
        if is_card(rel, fm):
            kind, status = fm.get(TYPE), fm.get(STATUS)
            if kind not in STATUSES:
                bad(MSG["type"], rel)
            elif status not in STATUSES[kind]:
                bad(MSG["status"], f'{rel}: "{status}"')
            if not summary_of(fm, text) and not self_described(rel, text):
                bad(MSG["summary"], rel)
            elif len(fm.get(SUMMARY, "")) > 160:
                bad(MSG["long"], rel)
            if len(text) > 6000:
                bad(MSG["big"], rel)
        if rel.startswith(INBOX) and fm.get(STATUS) == INBOX_NEW:
            bad(MSG["inbox"], rel)
        for link in sorted(set(LINK.findall(CODE.sub("", text)))):
            if link.strip().rstrip("\\").split("/")[-1] not in targets:
                bad(MSG["link"], f"{rel} → [[{link.strip()}]]")
    for stem, count in collections.Counter(n[1] for n in notes).items():
        if count > 1:
            bad(MSG["dup"], f"{stem} ×{count}")
    now = os.path.join(ROOT, NOW)
    if not os.path.exists(now):
        bad(NOW, MSG["now_missing"])
    else:
        days = int((time.time() - os.path.getmtime(now)) / 86400)
        lines = open(now, encoding="utf-8", errors="replace").read().count("\n") + 1
        if days > 14:
            bad(NOW, MSG["now_stale"].format(days))
        if lines > 50:
            bad(NOW, MSG["now_long"].format(lines))

    for kind, items in found.items():
        print(f"\n{kind} — {len(items)}")
        for item in items[:12]:
            print("  " + item)
        if len(items) > 12:
            print("  " + MSG["more"].format(len(items) - 12))
    total = sum(len(v) for v in found.values())
    print("\n" + MSG["result"].format(sum(is_card(n[0], n[2]) for n in notes), total))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    command = ARGS[0] if ARGS else ""
    if command == "list":
        cmd_list()
    elif command == "check":
        cmd_check()
    else:
        print(USAGE)
