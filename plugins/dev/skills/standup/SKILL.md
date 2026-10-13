---
name: standup
description: Write my daily standup in simple spoken English from my git and GitHub activity in any repository, optionally adding Linear activity and my own notes, in a chosen format.
argument-hint: "[linear] [format <name>] [since <day>] [repos <a,b>] [copy] [notes: <text>]"
disable-model-invocation: true
effort: low
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/collect.sh) Bash(${CLAUDE_SKILL_DIR}/scripts/collect.sh *) Bash(${CLAUDE_SKILL_DIR}/scripts/copy.sh *) Edit(~/.standup/**)
---

# Daily standup

Read-only toward code and issues: never modify files in repos, branches, PRs or Linear.
The only file you write is the history file in `~/.standup/`.

## Collected data and formats (default window, current repo)

!`${CLAUDE_SKILL_DIR}/scripts/collect.sh`

## Arguments

Parse `$ARGUMENTS` (all optional, any order; everything after `notes:` is notes):

| Argument | Effect |
|---|---|
| `linear` | Linear is REQUIRED for this run. |
| `format <name>` | Output format from the Output formats section of the collected data. Default: `classic`. |
| `since <day>` | Change the start date (`since friday`, `since 2 days`, `since 2026-10-10`). |
| `repos <a,b>` | Extra local repo paths to include. |
| `copy` | Copy the final standup to the clipboard. |
| `notes: <text>` | My own notes, Spanish or English. |

First write one line with what you parsed, e.g.
`Parsed: linear=yes · format=done-next · since=default · repos=current · copy=no · notes=yes`.

## Steps

1. **Re-collect if needed.** If `since`, `repos` or `linear` was passed, run the
   script again with flags (convert `since` to YYYY-MM-DD):
   `${CLAUDE_SKILL_DIR}/scripts/collect.sh --since <date> --repos <a,b> --linear`
   Otherwise use the collected data above.

2. **Linear** (only if `linear` was passed; then it is mandatory):
   - If the Linear section has data, use it.
   - If it says `LINEAR_API_KEY not set` or `LINEAR_ERROR`, use the Linear MCP
     tools: search for them first (e.g. ToolSearch "linear"), because they may be
     deferred. Get issues assigned to me updated since START, my comments since
     START, and the issues for ticket IDs found in git.
   - If nothing works, start the output with
     `⚠️ Linear was requested but is not available: <reason>. Check /mcp or set LINEAR_API_KEY.`

3. **Build one deduplicated list of items.** Group by ticket ID (pattern
   `[A-Z][A-Z0-9]+-[0-9]+` in branches, commits, PR titles and Linear) and by
   outcome. One ticket = one item across git, GitHub and Linear. Ignore trivial
   commits (typos, formatting, lint, wip). Each item gets a section:
   done, next or blocker. Open PRs waiting for approval are "next" or "blocker".

4. **Continuity.** If there is a previous standup, check what it said under
   Today/Next. Planned work that is now done → done. Planned work with no
   activity → keep it in next (do not invent progress).

5. **My notes** (if `notes:`): translate to English, split into facts. Same work
   as an existing item → merge it (add context or correct it, never duplicate).
   New work → new item. Section by meaning. If a note contradicts the data,
   trust the note. Never drop a note.

6. **Select and write** in the chosen format from the Output formats section of the collected data. Respect its item limits.
   Prioritize finished work, then blockers, then work in progress.

## Style rules
- Simple spoken English, B1 level, 8 to 12 words per sentence or bullet.
- Active voice, common verbs: finished, fixed, merged, started, pushed, reviewed.
  In bullet formats, start each bullet with the verb.
- Describe what changed for users or the team, not code details.
- No commit hashes, branch names, PR numbers, ticket IDs or file paths.
- If there was no activity and no notes, say so in one line.

## Save and copy
- Write the standup text only (no check line, no Parsed line) to
  `~/.standup/<today YYYY-MM-DD>.md`, replacing it if it exists.
- If `copy` was passed, run `${CLAUDE_SKILL_DIR}/scripts/copy.sh ~/.standup/<today>.md`.

## Check line
End with one short line for me:
`Sources: <repos> · <PRs and tickets used> · Linear: <used / not requested / unavailable: reason> · Notes: <merged into X / added / none> · Saved: ~/.standup/<today>.md`
