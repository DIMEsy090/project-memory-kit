# Set up project memory

This whole file is a task for you. Set up memory in the current project following the scheme below.

## Why

I work on a project for weeks, across many chats. My ideas and decisions must not get lost, and in any new chat you should find what you need quickly and at a low token cost. To get there, the project gets a vault: a folder of plain `.md` files. I open it in Obsidian; you read and write it as files.

Everything below follows from five rules. Where the scheme doesn't cover a case, decide by them.

1. **Little goes into context.** A chat starts with only the block in `CLAUDE.md` and `Now.md`. Everything else is found through a "name — summary" list and read one card at a time.
2. **One thought, one file**, and every file has a `summary` line in its properties. The card is found by that line without being opened.
3. **Every fact has one home.** Status lives only in the properties. Whatever stops being true gets a status or moves to `Archive/`; it does not sit next to what is current.
4. **Capture is immediate and visible.** An idea is written down in the same reply where it came up, and you report it in one line. That way I can see when something was not captured.
5. **A script keeps order**, not memory. A stale note is worse than a missing one, because you will trust it.

## Step 0. Look around and break nothing

- See what already exists: `CLAUDE.md`, `AGENTS.md`, a folder with `.obsidian`, `docs/`, notes.
- The default vault folder is `Vault/` in the project root.
- If the project already has a vault, do not rename or move its folders. Fit the scheme to it: change the settings at the top of the script (`CARDS`, `STATUSES` and their neighbours) and the folder names in the `CLAUDE.md` block. Show me what maps to what and wait for my "yes".
- Rewriting old cards in bulk is usually unnecessary. The script reads the type from a tag (`tags: [type/idea]`) and the summary from a `**Summary:**`, `**What:**` or `**Who:**` line in the text; a short card (up to 700 characters) needs no summary. Put reports and old documents into `ARCHIVE`, folders a script writes from code into `GENERATED`, and service note types into `NOT_CARDS`. Run `check` and show me how many issues remain and of what kind.
- Delete or move nothing without my "yes".

## Step 1. Structure

```
Vault/
├── Home.md        table of contents: one line per section with a link; no counts that will go stale
├── Now.md         up to 40 lines: where we stopped, what is next, what waits for my decision
├── Log.md         append-only: one line per event
├── Inbox/         raw material from me: thoughts, links, screenshots; you turn it into cards
├── Ideas/         what could be done; one card per idea, subfolders by topic
├── Decisions/     what was decided and why, when the decision is wider than one idea
├── Knowledge/     how things work now; subfolders that fit the project
├── Archive/       reports, old documents, long write-ups
├── Templates/
└── _memory.py
```

Pick the subfolders of `Knowledge/` to fit the project: "Mechanics" and "Characters" for a game; "Modules" and "Data" for software; "Topics" for study notes. In `Ideas/`, start a topic subfolder once a folder holds more than 40 cards: a folder's list has to stay short.

## Step 2. Templates

Create these four files in `Vault/Templates/` verbatim.

`Idea.md`:

```markdown
---
type: idea
status: new
summary:
tags: []
links: []
by: author
date: {{date}}
---
# {{title}}

## What and why

## Author's words
> "…" — date

## History
- date — status, who decided, why
```

`Decision.md`:

```markdown
---
type: decision
status: active
summary:
tags: []
links: []
date: {{date}}
---
# {{title}}

**Decided:**
**Why:**
**Rejected alternatives:**
**Replaces:**

## Author's words
> "…" — date
```

`Knowledge.md`:

```markdown
---
type: knowledge
status: current
summary:
tags: []
links: []
date: {{date}}
---
# {{title}}

**What it is:**
**How it works now:**

## Links
- [[…]] — why it is related

## Where in the project
- file, function, screen

## History
- date — what changed, link to the decision
```

`Inbox item.md`:

```markdown
---
type: inbox
status: new
date: {{date}}
---
# {{title}}

(what the author sent)

## Breakdown
(written by the AI: what this is, what to take from it, which cards were created or updated)
```

## Step 3. Script

Create `Vault/_memory.py` verbatim. It is already tested. If `python` is not found, try `py` or `python3` and write the command that worked into the `CLAUDE.md` block.

```python
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
```

## Step 4. Block in CLAUDE.md

This block is loaded into every chat, so it is short. Do not grow it: details live in the vault.

- If there is no `CLAUDE.md`, create one: 3–5 lines on what the project is, then the block below.
- If there is a `CLAUDE.md`, append the block and remove whatever the block now repeats.
- If the project has an `AGENTS.md` (other coding agents use it too), put the block there without its last `@` line, and leave two lines in `CLAUDE.md`: `@AGENTS.md` and `@Vault/Now.md`.

The block, verbatim:

```markdown
## Project memory: the `Vault/` folder (opens in Obsidian)

Everything known about the project lives in `Vault/`, not in chat. Use Claude's auto memory only for how to work with me; project knowledge goes into the vault, where I can see it in Obsidian.

**Starting work.** `Now.md` is pulled in by the last line of this block. If its text is not in context, read `Vault/Now.md`. Read everything else only when the task needs it.

**How to search, cheapest first.**
1. `python Vault/_memory.py list [folder] [--status status] [--find word]` — one line per card: status, name, summary.
2. Open the 1–5 cards you need and the ones in their `links`.
3. Do not search or read `Archive/` and `Inbox/` unless a card links there or I ask.
4. Read `Log.md` from the end, the last 20 lines.

**How to capture: at once, in the same reply.**
- I voice an idea → first `list --find` to see whether it exists. If it does, extend that card; if not, create a card in `Ideas/` from the template. My words go in as an exact quote, with the date.
- We decide something → change the idea's `status` and add a line to its "History": date, who decided, why. A decision wider than one idea → a card in `Decisions/`.
- How something works has changed → update its card in `Knowledge/` and the card's `date`.
- After writing, say so in chat in one line: `📌 [[Card name]] — what was recorded`. No such line means nothing was recorded.
- Delete nothing: change the status and write the reason.

**A card.** One file, one thought. Required properties: `type`, `status`, `summary` (one line of up to 150 characters that makes sense on its own; quote it if it contains a colon), `date`. A short card (up to 700 characters) can skip the summary if its name says it all. Status lives only in the properties. Links are always `[[Name]]`; note names are unique. A card longer than 80 lines → split it or move the details to `Archive/` with a link.

**Statuses.** Idea: new · decided · in progress · done · postponed · rejected · replaced. Decision: active · replaced. Knowledge: current · draft · outdated.

**What to trust.** Code and facts → `Knowledge/` → `Decisions/` → `Archive/`. If you find a mismatch, mark the card with `⚠ mismatch` and tell me.

**Subagents** get paths to the cards they need, not a request to "study the vault".

**Finishing work** — when I write "wrap up" or the topic is closed:
1. Go through the conversation: any ideas or decisions left without a card?
2. Rewrite `Now.md` from scratch, up to 40 lines: where we stopped, what is next, what waits for my decision.
3. Append a line to `Log.md`: `## [YYYY-MM-DD] what was done — [[links]]`.
4. Run `python Vault/_memory.py check` and fix what it finds.

@Vault/Now.md
```

## Step 5. Ideas table for Obsidian

Create `Vault/Ideas/All ideas.base` so that I can see ideas as a table grouped by status:

```yaml
filters:
  and:
    - note["type"] == "idea"
properties:
  note.status:
    displayName: Status
  note.summary:
    displayName: Summary
  note.by:
    displayName: By
  note.date:
    displayName: Date
views:
  - type: table
    name: All ideas
    groupBy:
      property: status
      direction: ASC
    order:
      - file.name
      - summary
      - by
      - date
  - type: table
    name: Waiting for a decision
    filters:
      or:
        - note["status"] == "new"
    order:
      - file.name
      - summary
      - date
  - type: table
    name: Decided, not done
    filters:
      or:
        - note["status"] == "decided"
        - note["status"] == "in progress"
    order:
      - file.name
      - summary
      - date
```

If the project uses git, add the line `Vault/.obsidian/workspace*.json` to `.gitignore`.

## Step 6. If the project already has documents, notes or an old vault

Inventory first, migration second.

- Show me a "what exists → where it goes" table: Knowledge, Ideas, Decisions, Archive or "leave alone", with file counts. Wait for my "yes".
- Do not chop a long document into cards wholesale. Put it in `Archive/` and extract into cards only what is true now, with a link to the source.
- Ideas and decisions found in documents and chats get one card each, with a quote and a date, and the status they actually have.
- If there are more than a hundred cards, migrate with a script and show me three sample cards before the bulk run.
- If Claude's auto memory for this project holds knowledge about the project itself, list it and offer to move it into the vault.

## Step 7. Fill in and check

- `Now.md`: what the project is, where we stopped, what is next, what waits for my decision. Up to 40 lines.
- `Home.md`: one line per folder and per key card.
- `Log.md`: a first line saying the vault was created.
- Run `python Vault/_memory.py check` and `python Vault/_memory.py list`. Fix what they find.

## Step 8. Report

Write me no more than 10 lines: what was created, what was adapted to the project, what waits for my "yes", and the output of `check`. Remind me of the two habits I use: any idea in chat is captured automatically and confirmed with a `📌` line, and the words "wrap up" close a work session.
