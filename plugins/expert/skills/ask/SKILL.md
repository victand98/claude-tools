---
name: ask
description: Answer a question about the current project, business or technical, from my personal knowledge base first, then the code, git history, the code graph and connected MCP servers, and save what was learned back to the knowledge base. Use when I ask how or why something in this project works, what a term or entity means, where something lives, who owns an area, or what the business reason behind a feature is. Not for making code changes.
argument-hint: "<question> [--no-save] [es]"
effort: high
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py *) Bash(git log *) Bash(git show *) Bash(git blame *) Bash(git shortlog *) Read(~/.expert/**) Edit(~/.expert/**) Write(~/.expert/**)
---

# Ask the project expert

Read-only toward the project: never edit, commit or push anything in the repository or any external tool.
The only place you write is the vault.

## State

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py status --repo "${CLAUDE_PROJECT_DIR}" || true`

Script: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py <status|pages|scaffold|commit "<msg>"|lint> [--repo DIR]`.
Page rules: `<vault>/SCHEMA.md` (read it once before writing a page).

## Arguments

`$ARGUMENTS` = the question plus optional flags, in any order:
- `--no-save`: answer only, write nothing.
- `es`: after the English answer, add a short **En español** section explaining the same in Spanish.

If there is no question, ask me for one.

## Steps

1. **Knowledge base first.** If the project has a KB (`project.exists`), read `index.md`, then only the pages
   that look relevant (check `topics/` and `concepts/` too). If they answer the question:
   - Compare each page's `verified_commit` with the repo HEAD. If its `sources` changed since then
     (`git diff --stat <verified_commit>..HEAD -- <paths>`), re-check those parts in the code before answering.
   - Answer from the pages, cite them as `[[page]]`, and skip to step 4 (only update what was stale).

2. **Investigate** what the KB doesn't cover, cheapest source first:
   1. Code graph: if tools from `codebase-memory-mcp` exist (find them with ToolSearch, query
      `codebase-memory`), use `search_graph`, `trace_path`, `get_architecture`, `search_code`. If the
      project isn't indexed yet, run `index_repository` once.
   2. Code: Grep/Glob/Read. For broad questions touching many areas, delegate the sweep to the
      `expert:researcher` agent and work from its brief.
   3. History, for the *why*: `git log -S '<symbol>' --oneline`, `git log --follow -- <file>`, `git blame -L`.
      Follow PR and issue numbers in commit messages.
   4. Business context from connected MCP servers, when the question has a business side or the code
      doesn't explain the why: ToolSearch for `github`, `linear`, `jira`, `notion`, `confluence`, `slack`,
      `drive`, `figma`, and use whatever is there (read-only). Don't mention tools that aren't connected.
   Stop when you can answer with evidence; don't read the whole repo.

3. **Answer** in this shape (simple, clear English):
   - **Answer**: 2–5 sentences, the direct answer first.
   - **Business view** and **Technical view**: include each one that applies.
   - **Evidence**: `path:line` references, commits, PR/issue links, KB pages.
   - **Confidence** (high / medium / low) and **open questions**, if any.
   - Optional: one small Mermaid diagram when a flow or relationship is easier to see than read.

4. **Save** (skip with `--no-save`). Save only if the answer needed real investigation: several files,
   git history or MCP tools. Don't save trivial lookups (a single definition, one config value).
   - If `project.exists` is false, run `expert.py scaffold --repo "${CLAUDE_PROJECT_DIR}"` first.
   - Update the best matching existing page, or create `topics/<kebab-topic>.md`. Follow SCHEMA.md: frontmatter
     with `sources`, `verified_commit` = repo HEAD, today's date, `confidence`; business and technical views;
     `[[wikilinks]]` to related pages. If the knowledge is not project-specific (a pattern, a library),
     write it to `<vault>/concepts/` and link it.
   - Add new pages to `index.md` (one line each, right section) and append one line to `log.md`:
     `- YYYY-MM-DD · <question> → [[page]]`.
   - Never write secrets, tokens, `.env` values, personal or customer data: point to where they live.
   - Run `expert.py commit "ask: <short question>"`.
   - End with one line: `Saved → projects/<slug>/<page>` (or `Not saved: <reason>`). If the commit result
     says `queued`, add `(will sync on next commit)`.
