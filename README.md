# victor-tools

Personal Claude Code plugin marketplace.

## Install

In a Claude Code session:

```
/plugin marketplace add victand98/claude-tools
/plugin install dev@victor-tools
```

The repo is public, so no GitHub login is needed.

## Updates

The plugin has no `version`, so every pushed commit is a new version.

- Manual: `/plugin marketplace update victor-tools`
- Automatic: `/plugin` → Marketplaces → victor-tools → Enable auto-update

## Plugins

### dev

| Command | What it does |
|---|---|
| `/dev:standup` | Daily standup in simple spoken English from git, GitHub and optionally Linear |

`/dev:standup` arguments (all optional):

```
/dev:standup [linear] [format <name>] [since <day>] [repos <a,b>] [copy] [notes: <text>]
```

- Formats live in `plugins/dev/skills/standup/formats.md`.
- History is saved in `~/.standup/`.
- Linear: set `LINEAR_API_KEY`, or connect the Linear MCP (`/mcp`).

### design

```
/plugin install design@victor-tools
```

| Command | What it does |
|---|---|
| `/design:redesign-page <page> <goal>` | Figma-first redesign or migration of a screen onto the project's design system |

Works in any project: it reads the project's own design docs (`DESIGN.md`, `CLAUDE.md`, `AGENTS.md`,
`.claude/rules/`) and asks for anything it cannot find, such as the Figma library file, breakpoints, themes and
verification commands. It only runs by explicit command.

Requirements: the Figma MCP connector, ideally with the Figma plugin skills (`figma-use`,
`figma-generate-library`, `figma-generate-design`).

### english

Guía completa en español: [plugins/english/README.md](plugins/english/README.md)

```
/plugin install english@victor-tools
```

| Command | What it does |
|---|---|
| `/english:phrase <phrase> -- <context>` | Explains the phrase in Spanish and creates two Anki cards (recognize + produce) |
| `/english:phrase transcript: <text>` | Picks the 5–8 most useful phrases from a meeting transcript or chat |
| `/english:phrase review [days]` | Weekly review: stats, hardest cards (with rewrites) and a short roleplay |
| `/english:phrase setup` | Creates the `English::Phrases` deck, the `English Phrase` note type and a preset (10 new/day, bury siblings) |

Requirements (once per machine):

1. Anki desktop open, with the AnkiConnect add-on (code `2055492159`).
2. `python3` (standard library only).
3. AnkiWeb login in Anki and on the phone (AnkiDroid/AnkiMobile) so cards sync.
4. In Anki: enable FSRS, desired retention 0.90, leech action "Tag only".

If Anki is closed, notes are queued in `~/.english-phrases/pending.json` and added on the next run.
Audio uses Anki's built-in TTS (`{{tts en_US:...}}`), so voices come from the OS.

### expert

Full guide: [plugins/expert/README.md](plugins/expert/README.md)

```
/plugin install expert@victor-tools
```

| Command | What it does |
|---|---|
| `/expert:onboard [deep] [vault <owner/name>]` | Builds a knowledge base for the current repo (overview, glossary, architecture, domain, people, decisions, map, reading path) |
| `/expert:ask <question>` | Answers from the knowledge base first, then code, git history, code graph and MCP servers; saves what it learns |
| `/expert:map <type> [html]` | Mermaid map: architecture, domain, flow, deps, owners or the KB itself |
| `/expert:quiz [topic]` | Anki flashcards (or a chat quiz) from the knowledge base |
| `/expert:lint [fix]` | Finds pages whose source code changed, plus broken links and orphans |

The knowledge base is a Markdown git repo (keep it private), synced across devices and readable in Obsidian.

## Develop

```
claude plugin validate .
claude --plugin-dir ./plugins/dev     # test changes without installing
```
