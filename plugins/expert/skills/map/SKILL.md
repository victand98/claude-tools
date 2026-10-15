---
name: map
description: Draw a diagram of the current project - architecture, domain model, a feature's flow, dependencies or code owners - as Mermaid in my knowledge base, optionally as an interactive HTML page.
argument-hint: "<architecture|domain|flow <feature>|deps|owners|kb> [html] [es]"
disable-model-invocation: true
effort: high
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py *) Bash(git log *) Bash(git shortlog *) Read(~/.expert/**) Edit(~/.expert/**) Write(~/.expert/**)
---

# Project map

Read-only toward the project. Write only in the vault.

## State

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py status --repo "${CLAUDE_PROJECT_DIR}" || true`

## Map types (`$ARGUMENTS`; default `architecture`)

| Type | Shows | Mermaid | Best sources |
|---|---|---|---|
| `architecture` | apps/services, data stores, queues, external APIs, who calls whom | `flowchart LR` with subgraphs per boundary | `get_architecture`, manifests, IaC, env config names |
| `domain` | core entities, key fields, relations, cardinality | `erDiagram` (or `classDiagram`) | models, schemas, migrations |
| `flow <feature>` | one request or job end to end: entry → handlers → domain → stores → side effects | `sequenceDiagram` | `trace_path`, routes, handlers |
| `deps` | internal modules/packages and their dependencies | `flowchart TD`, max ~25 nodes, grouped | `query_graph`, imports |
| `owners` | top-level areas → main people (last 12 months) | `flowchart LR` | `git log --format='%an' -- <dir>` |
| `kb` | the knowledge base itself: pages and their wikilinks | `flowchart LR` | `expert.py pages` + wikilinks in pages |

Flags: `html` also publishes an interactive page; `es` adds a short Spanish explanation.

## Steps

1. If the project has a KB, read `index.md` and the pages for this map type first; reuse what they say.
2. Gather facts from the cheapest source (codebase-memory-mcp tools via ToolSearch `codebase-memory`
   when present, else Grep/Read/git). Every node and edge must come from something you read.
3. Diagram rules: max ~25 nodes (group the rest), labels in plain words with the code name in brackets
   when useful (`Orders API [orders-svc]`), edges labelled with the verb or protocol, external systems
   visually separate. Validate the Mermaid syntax mentally: quote labels with special characters.
4. If `project.exists` is false, run `expert.py scaffold --repo "${CLAUDE_PROJECT_DIR}"`. Write
   `maps/<type>[-<feature>].md` per SCHEMA.md (`type: map`, `sources`, `verified_commit` = HEAD), with: the
   diagram, a **How to read it** section (5–8 bullets, business meaning first), and `[[wikilinks]]` to the
   pages each part relates to. Add it to the **Maps** section of `index.md`, append to `log.md`, and run
   `expert.py commit "map: <type>"`.
5. `html`: if the Artifact tool is available, build a single page that renders the same diagram
   (Mermaid from cdnjs, pinned version), with clickable nodes that show each node's description and sources,
   and publish it. Otherwise say that HTML needs the Artifact tool and skip it.

## Output to me

Show the diagram in the chat, the "How to read it" bullets, and one line: `Saved → projects/<slug>/maps/<file>`.
