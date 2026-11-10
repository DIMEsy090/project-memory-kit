# Project Memory Kit

**English** · [Русский](README.ru.md)

One prompt that gives a project a long-term memory an AI coding agent can use: plain Markdown cards in a folder you can open in Obsidian, a 34-line block of rules in `CLAUDE.md`, and a small script that lists and checks the cards.

Built for [Claude Code](https://code.claude.com/docs). It should suit any agent that reads project files and an instructions file such as `AGENTS.md`, but only Claude Code has been tried. Not affiliated with Anthropic or Obsidian.

**Status:** early. Read [What was tested](#what-was-tested-and-what-was-not) before relying on it.

## The problem

A long project with an AI agent leaks. An idea voiced in chat is gone after the next `/clear`. Decisions get argued again because nobody recorded why. Each new chat either starts from zero or re-reads large documents, which costs tokens and makes answers worse.

## How it works

The setup prompt creates a vault inside your project:

```
Vault/
├── Now.md         where we stopped, what is next; up to 40 lines, rewritten each session
├── Log.md         one line per event, append-only
├── Home.md        table of contents
├── Inbox/         raw material from you: thoughts, links, screenshots
├── Ideas/         one card per idea, with a status
├── Decisions/     what was decided and why
├── Knowledge/     how things work now
├── Archive/       reports and old documents; not read by default
├── Templates/
└── _memory.py     lists cards and checks the vault
```

Every card is one file with a few properties:

```yaml
---
type: idea
status: new
summary: Players buy shares of nearby companies first, exchanges open later
tags: [economy]
links: ["[[Market]]"]
by: author
date: 2026-11-10
---
```

The `summary` line is what makes this cheap. The agent does not open cards to find out what they are. It runs one command and gets one line per card:

```
$ python Vault/_memory.py list Ideas --status new

# Ideas/Economy
[new] Stock trading — Players buy shares of nearby companies first, exchanges open later
[new] Second currency — Coins for premium goods, earned only through orders

total: 2
```

Then it opens only the cards it needs.

| When | What enters the context | Cost, estimated |
|---|---|---|
| Every chat | The rules block in `CLAUDE.md` and `Now.md` | about 1,200 tokens |
| Searching | `list` output, one line per card | roughly 40–60 tokens per card |
| Reading | One card | 300–1,000 tokens |
| Wrapping up | `check` output, capped at 12 items per category | a few hundred tokens |

You work with two habits:

- **Say an idea in chat.** The agent writes or updates a card in the same reply and confirms it with a line like `📌 [[Stock trading]] — added the dividends rule`. No such line means nothing was recorded.
- **Say "wrap up".** The agent sweeps the conversation for ideas and decisions without a card, rewrites `Now.md`, appends a line to `Log.md`, and runs the check.

## Quick start

1. Open your project in Claude Code.
2. Paste the text of [`en/PROMPT.md`](en/PROMPT.md), or tell Claude to follow the instructions in that file.
3. Answer its questions. If the project already has documents, it shows a plan and waits for your "yes" before moving anything.
4. Optionally open `Vault/` in Obsidian as a vault.

Requires Python 3; the script uses only the standard library. A Russian version with Russian folder names, properties and statuses is in [`ru/PROMPT.md`](ru/PROMPT.md).

## Who it is for

- You run one project for weeks or months with an AI agent and keep starting new chats.
- You think out loud in chat and lose ideas, or re-argue decisions you already made.
- You want to see the project's knowledge yourself: as files, as tables, as a graph in Obsidian.
- You watch token costs and do not want to run a memory server.

It fits game design, product work, research and study notes as well as code.

## Who it is not for

- Teams that need permissions, concurrent editing or review workflows.
- Collections of tens of thousands of documents, or anything that needs semantic search.
- People who want memory that is fully automatic with no upkeep.
- Short one-off tasks. A plain `CLAUDE.md` is enough there.

## Pros

- **Plain files.** No server, database, plugin or MCP. It works offline, diffs in git, and a human can read it in Obsidian or any editor.
- **Small fixed cost.** About 650 tokens of rules plus `Now.md` per chat. Everything else is loaded on demand.
- **Cheap discovery.** One line per card, filtered by folder, status or word.
- **Misses are visible.** Every capture is confirmed with a `📌` line, so a missing line means a missing card.
- **Decisions keep their reasons.** Nothing is deleted. A rejected idea keeps its status and the reason, so the agent stops proposing it again. Your words are stored as exact quotes.
- **A script keeps order.** It finds broken links, statuses outside the dictionary, missing summaries, duplicate names, oversized cards and a stale `Now.md`. It exits with code 1 on problems, so it can run as a pre-commit hook.
- **One prompt to install**, and it asks before touching existing documents.

## Cons

- **Rules, not enforcement.** Capture depends on the model following the block in `CLAUDE.md`. The `📌` line exposes a miss; it does not prevent one.
- **Word match only.** `--find` is a substring search over names, summaries and tags. A synonym will not match.
- **Upkeep costs tokens.** A card for every idea and a rewritten `Now.md` are output you pay for, and summaries have to stay honest.
- **A stale `Now.md` hurts,** because it is loaded into every chat. The check flags it after 14 days; before that it is on you.
- **Simple parser.** The script reads top-level `key: value` properties with regular expressions, not a YAML parser. Nested properties are ignored.
- **One language per vault.** Folder names, property keys and statuses are fixed per language version.
- **Single writer.** There is no locking. Two agents editing one card at once will conflict, and git is the only safety net.
- **Young.** One author, one real vault.

## What was tested and what was not

Tested:

- The script, in both languages: `python tests/test_kit.py` builds a clean and a broken sample vault and runs 32 checks.
- The script, read-only, on a real private vault of 1,223 notes (about 5.3 million characters of Russian text): `check` finished in 0.3 seconds.
- Windows 11, Python 3.12, from PowerShell and Git Bash.

Not tested yet:

- The setup prompt end to end on a fresh project.
- The `.base` table in Obsidian. It follows the syntax of a base that works in the author's vault, but this exact file has not been opened.
- The `@Vault/Now.md` import with a non-ASCII path, as used in the Russian version.
- macOS and Linux, and agents other than Claude Code.

Token figures in this file are estimates from character counts (about 4 characters per token for English, about 2.8 for Russian), not tokenizer output.

## Background

The scheme came out of auditing a real game-design vault that had grown to 1,223 notes. The cards worked: a task about one mechanic needed an estimated 5,000–8,000 tokens of context. The losses were around the cards:

- Reports and old documents made up 68% of the text and sat in the same search space as the cards. A typical report was about 6,700 tokens.
- The "where we stopped" note was three weeks old, and the home page quoted counts that were no longer true.
- Status was stored in three places per card, and nine cards used statuses outside the agreed list.
- Nothing in the project told a new chat that the vault existed. The pointer lived in the agent's machine-local memory, tied to one folder.
- There was no cheap list of ideas. Listing 67 of them by name alone took about 1,500 tokens, and 285 cards had no summary to show.

Each rule in the kit answers one of these.

## Related work

- **[Karpathy's LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** describes the general pattern: raw sources, a wiki the LLM maintains, a schema file, an index and a log. This kit is one concrete take on it, aimed at your own ideas and decisions rather than at ingesting external sources. It adds statuses, a `summary` property and a check script.
- **[Claude Code auto memory](https://code.claude.com/docs/en/memory)** is written by Claude and stored per machine. The kit complements it: preferences about how to work stay there, project knowledge goes into the vault.
- **[A report on running an LLM wiki at scale](https://mpt.solutions/karpathys-llm-wiki-works-heres-what-broke-when-i-ran-it-at-real-scale/)** lists what breaks: stale reference sections, silent contradictions, orphan pages. Its fix is a linter that runs on every commit, which is why the check script exists.
- **[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** by Anthropic argues for the smallest set of high-signal tokens and for loading context just in time.
- **[Letta's memory benchmark](https://www.letta.com/blog/benchmarking-ai-agent-memory)** found that an agent with plain files and grep scored 74.0% on LoCoMo against 68.5% reported for a specialised memory system. It is one vendor's result, but it supports starting with files.

## Adapting and contributing

- To rename folders or change statuses, edit the settings at the top of `_memory.py` and the matching names in the `CLAUDE.md` block.
- To run the check on every commit, call `python Vault/_memory.py check` from a pre-commit hook.
- The script exists twice: as `en/_memory.py` and `ru/_memory.py`, and inside each `PROMPT.md`. After editing a script, run `python tools/embed.py` and then `python tests/test_kit.py`. The test fails if the copies differ or if the logic differs between languages.

Issues and pull requests are welcome, especially reports from real projects.

## License

[MIT](LICENSE)
