---
name: lint
description: Health check of my knowledge base for the current project - pages whose source code changed since they were verified, missing sources, broken wikilinks, orphan pages, pages missing from the index and oversized pages - and optionally fix them.
argument-hint: "[fix] [es]"
disable-model-invocation: true
effort: medium
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py *) Bash(git diff *) Bash(git log *) Read(~/.expert/**) Edit(~/.expert/**) Write(~/.expert/**)
---

# Knowledge base lint

Read-only toward the project. Write only in the vault, and only with `fix`.

## Report

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py lint --repo "${CLAUDE_PROJECT_DIR}" || true`

If the report has an `error`, show it with the suggested command and stop.

## Without `fix`

Summarize for me, most important first:
1. **Stale**: pages whose sources changed since `verified_commit` (show changed lines and files).
   For the top 3, run `git diff <verified_commit>..HEAD -- <files>` and say in one line whether the change
   likely affects what the page claims.
2. **Missing sources** (files moved or deleted) and **unverifiable** pages.
3. **Structure**: broken links, orphans, pages not in `index.md`, pages without frontmatter, pages over
   150 lines.
4. **Contradictions**: skim pages that cover the same topic (same tags or linked to each other) and list
   claims that disagree.
End with: `Run /expert:lint fix to repair these.` If everything is clean, say so in one line.

## With `fix`

Read `<vault>/SCHEMA.md` first. Then, in this order:
1. Stale pages: re-read the changed code, correct the page, set `verified_commit` to the report's `head`
   and `updated` to today. If nothing the page says changed, only bump `verified_commit`.
2. Missing sources: find where the code moved (`git log --follow --name-status -- <old path>` or Grep)
   and update `sources`; if the feature was removed, mark the page `confidence: low` and add a note.
3. Broken links: point them to the right page or remove them. Orphans and pages missing from the index:
   add them to `index.md` and link them from a related page.
4. Oversized pages: split them into `topics/` pages and link them.
5. Contradictions: resolve with the code as the source of truth, or move them to **Open questions**.
Append `- YYYY-MM-DD · lint fix → …` to `log.md`, run `expert.py commit "lint: fix <n> issues"`, then
re-run `expert.py lint` and report before → after counts.

`es`: add a short Spanish summary at the end.
