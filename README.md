# victor-tools

Personal Claude Code plugin marketplace.

## Install

In a Claude Code session:

```
/plugin marketplace add victand98/claude-tools
/plugin install dev@victor-tools
```

For a private repo, git must authenticate without prompts. Once per machine:

```
gh auth login
gh auth setup-git
```

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

### english

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

## Develop

```
claude plugin validate .
claude --plugin-dir ./plugins/dev     # test changes without installing
```
