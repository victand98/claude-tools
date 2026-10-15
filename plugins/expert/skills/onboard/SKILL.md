---
name: onboard
description: Build or refresh my knowledge base for the current repository - overview, glossary, architecture, domain, people, decisions, a starter architecture map and a first-week reading path - from the code, git history, docs and connected MCP servers.
argument-hint: "[deep] [refresh] [vault <owner/name>] [es]"
disable-model-invocation: true
effort: high
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py *) Bash(git log *) Bash(git show *) Bash(git shortlog *) Bash(git ls-files *) Read(~/.expert/**) Edit(~/.expert/**) Write(~/.expert/**)
---

# Onboard to this project

Read-only toward the project. Write only in the vault.

## State

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py status --repo "${CLAUDE_PROJECT_DIR}" || true`

Script: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py <status|init <owner/name>|scaffold|commit "<msg>"|lint> [--repo DIR]`.

## Arguments (`$ARGUMENTS`, all optional)

| Argument | Effect |
|---|---|
| `vault <owner/name>` | Set the vault repo (`expert.py init <owner/name>`) before anything else. |
| `deep` | Index with codebase-memory-mcp first (if present) and go deeper on flows and history. |
| `refresh` | The KB exists: re-verify core pages against the code instead of skipping them. |
| `es` | End with a short summary in Spanish. |

## Steps

0. **Vault.** If `vault.repo` is empty and no `vault` argument was given, tell me in one line that the vault is
   local-only, and that `/expert:onboard vault <owner/name>` (a **private** repo) syncs it across devices.
   Then continue; don't block.
1. **Scaffold**: `expert.py scaffold --repo "${CLAUDE_PROJECT_DIR}"`. Read `<vault>/SCHEMA.md`.
   If the KB already has core pages and `refresh` wasn't passed, only fill the missing ones.
2. **Gather** (use the `expert:researcher` agent for broad sweeps; keep your own context small):
   - **Product and business**: README, `docs/`, landing copy, package descriptions, marketing or pricing
     code, analytics events, feature flags. Connected MCP servers (ToolSearch: `github`, `linear`,
     `jira`, `notion`, `confluence`, `drive`, `slack`, `figma`): project descriptions, epics, recent
     roadmap issues, specs. Read-only.
   - **Architecture**: manifests (package.json, pyproject, go.mod, pom, Dockerfile, compose, IaC, CI),
     entry points, services and data stores, external integrations. If codebase-memory-mcp tools exist,
     use `get_architecture` (run `index_repository` first when `deep` or not indexed).
   - **Domain**: models, schemas, migrations, core types, enums, and the business rules around them.
   - **People**: `git shortlog -sn --since=12.months`, and per top-level area
     `git log --format='%an' --since=12.months -- <dir> | sort | uniq -c | sort -rn | head -3`.
     CODEOWNERS if present. Names only, no emails.
   - **Decisions**: ADRs, `docs/decisions`, large or reverted PRs, commits with "because", "instead of",
     "migrate", "deprecate".
   - **Hotspots**: `git log --since=6.months --name-only --format= | sort | uniq -c | sort -rn | head -20`.
3. **Write pages** per SCHEMA.md (frontmatter, sources, `verified_commit` = HEAD, business + technical views,
   wikilinks): `overview`, `glossary`, `architecture`, `domain`, `people`, `decisions`. Keep each under
   ~150 lines; move details into `topics/`. Never copy secrets or personal data.
4. **Map**: write `maps/architecture.md` with a Mermaid `flowchart` of the main components, stores and
   integrations (the same rules as `/expert:map`).
5. **Index**: fill `index.md`. List every page with one line, plus a **First-week reading path**: the 8–10
   files in the repo to read in order (path + why), from entry point to core domain.
6. **Log and commit**: append `- YYYY-MM-DD · onboard → …` to `log.md`, then
   `expert.py commit "onboard: <slug>"`.

## Output to me

- 5–8 bullets: what this project is, for whom, how it's built, the 3 most important concepts.
- Pages written (one line), commit result, and suggested next steps:
  `/expert:ask <first question>`, `/expert:map domain`, `/expert:quiz`.
