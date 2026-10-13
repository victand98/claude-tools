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

## Develop

```
claude plugin validate .
claude --plugin-dir ./plugins/dev     # test changes without installing
```
