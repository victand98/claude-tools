# expert

Become an expert in any project, from day one. Ask questions about the repository you're in. Claude answers
from your **personal knowledge base** first, then from the code, git history, a code graph and any connected
MCP servers (GitHub, Linear, Notion, Slack, Figma…). It saves what it learns back to the knowledge base as linked
Markdown pages, so the knowledge grows with every question and follows you to every device.

```
/plugin install expert@victor-tools
```

| Command | What it does |
|---|---|
| `/expert:onboard [deep] [vault <owner/name>]` | Builds the KB for the current repo: overview, glossary, architecture, domain, people, decisions, an architecture map and a first-week reading path |
| `/expert:ask <question> [--no-save] [es]` | Answers a business or technical question: KB first, then code, history, code graph and MCP servers. Saves substantial answers to `topics/` |
| `/expert:map <architecture\|domain\|flow <feature>\|deps\|owners\|kb> [html]` | Mermaid diagram saved in the KB; `html` also publishes an interactive page |
| `/expert:quiz [topic] [n 10] [chat]` | Flashcards from the KB into Anki (`Expert::<project>` deck), or a quiz in the chat |
| `/expert:lint [fix]` | Finds pages whose source code changed since they were verified, plus broken links, orphans and index gaps; `fix` repairs them |

You don't need `/expert:ask` for every question. Ask normally ("how do refunds work here?") and Claude
uses the skill by itself. Add `es` to any command for a short explanation in Spanish.

## Setup (once)

1. Create a **private** repo for the vault, e.g. `victand98/expert-vault` (it can be empty).
2. Tell the plugin about it, either in `/plugin` → expert → configure (`vault_repo`), or with
   `/expert:onboard vault victand98/expert-vault`. The setting is saved in `~/.expert/config.json`.
   Without a repo the vault is local only (`~/.expert/vault`).
3. Optional, recommended: install the code graph,
   [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (MIT, single binary). Its
   installer registers it with Claude Code:
   ```
   curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
   ```
   Without it the plugin falls back to Grep/Read/git.
4. Optional: Anki desktop with AnkiConnect (add-on `2055492159`) for `/expert:quiz`.
5. Optional: open `~/.expert/vault` in Obsidian for graph view and backlinks, on desktop or phone (sync it with
   the same GitHub repo through the Obsidian Git plugin).

## How it works

- **Vault** = a git repo of Markdown pages following the
  [LLM-wiki pattern](https://blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide), with rules in
  `SCHEMA.md` and one folder per project (`projects/<owner-repo>/`) that has an `index.md`. Pages cite their
  `sources` and record the `verified_commit`, which is how `/expert:lint` detects drift.
- **SessionStart hook**: in any git repo it pulls the vault (15 s timeout, offline-safe) and gives Claude
  the project's `index.md`, so Claude knows what you already know.
- **Commits**: every write runs `expert.py commit`, which pulls with rebase and then pushes. When offline, the
  commit is kept and pushed next time. On a merge conflict it stops and tells you; it never force-pushes.
- **Privacy**: pages never contain secrets, tokens, `.env` values or personal or customer data, only where
  they live. Keep the vault repo private.

### Other devices

| Where | How |
|---|---|
| Any computer with Claude Code | Install the plugin. The first session clones the vault. |
| Claude Code on the web (cloud sessions) | Add the vault repo to the session (or environment) so git can reach it, then use the commands normally. |
| Phone | Obsidian + Obsidian Git on the vault repo to read and browse the graph, or a cloud Claude Code session to ask. |

## Files

- `scripts/expert.py`: vault helper (`status`, `init`, `ensure`, `scaffold`, `pages`, `commit`, `lint`, `hook`). Python standard library only.
- `skills/quiz/scripts/anki.py`: AnkiConnect client (Basic note type, offline queue).
- `agents/researcher.md`: read-only investigator used for broad sweeps.
- `templates/`: `SCHEMA.md`, vault README, project `index.md` and `log.md`.

## Next ideas (not in v1)

- [Basic Memory](https://github.com/basicmachines-co/basic-memory) MCP on the same folder for semantic search.
- [Graphify](https://claudelog.com/claude-code-mcps/graphify) to pull PDFs, slides and images into the graph.
- A small remote MCP over the vault so Claude on claude.ai web and mobile can query it.
