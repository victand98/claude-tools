# Vault schema

Rules every page in this vault follows. Claude reads this file before writing pages.

## Layout

```
SCHEMA.md                 this file
projects/<slug>/          one folder per repository (slug = owner-name from the git remote)
  index.md                map of every page with a one-line summary — read first
  overview.md             what the product is, who uses it, why it exists, how it makes money
  glossary.md             business and technical terms, one line each
  architecture.md         components, data stores, integrations, deployment
  domain.md               core entities, their relations and business rules
  people.md               who owns which area (from git history and trackers)
  decisions.md            key decisions and their reasons (ADRs, PRs, issues)
  topics/<topic>.md       answers to specific questions, built up over time
  maps/<name>.md          Mermaid diagrams
  log.md                  append-only log of questions and pages touched
concepts/<name>.md        knowledge that is not specific to one project
```

## Page format

```markdown
---
title: Payment retries
type: topic            # overview | glossary | architecture | domain | people | decisions | topic | map | concept
sources:               # where each fact came from; repo-relative paths, optionally #symbol or #L10-40, or URLs
  - src/payments/retry.ts#scheduleRetry
  - https://github.com/acme/shop/pull/412
verified_commit: 1a2b3c4   # repo HEAD when the sources were last checked against this page
updated: 2026-10-15
confidence: high       # high = read in code; medium = inferred; low = from docs or people, not confirmed
tags: [payments, jobs]
---

# Payment retries

**In one line:** …

## Business view
Why it matters, who cares, what breaks for users if it fails.

## Technical view
How it works, with `path/file.ts:line` references.

## Related
- [[architecture]] · [[domain]] · [[topics/billing-cycle|Billing cycle]]

## Open questions
- …
```

## Rules

1. One idea per page. Split pages that grow past ~150 lines.
2. Link generously with `[[wikilinks]]` (by file name, no `.md`). Every page links to at least one other page
   and is listed in `index.md`.
3. Every fact has a source. Prefer code over docs, docs over memory. Mark guesses as such.
   `sources` entries are repo paths (checked by `/expert:lint`), URLs, or short free text such as
   `git shortlog -sn (12 months)` for evidence that has no file.
4. Never copy secrets, credentials, tokens, `.env` values, personal data or customer data. Point to where they
   live (`config/prod.yaml:12`) instead.
5. When code and page disagree, the code wins: update the page and bump `verified_commit`.
6. Contradictions between sources go under **Open questions** with both sources.
7. English for pages. Code identifiers exactly as in the code.
