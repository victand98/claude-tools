---
name: quiz
description: Turn my knowledge base for the current project into spaced-repetition flashcards in Anki (business and technical, one fact per card), or quiz me in the chat when Anki isn't available.
argument-hint: "[<topic or page>] [n <count>] [chat] [flush] [es]"
disable-model-invocation: true
effort: medium
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py *) Read(~/.expert/**) Write(~/.expert/**)
---

# Project quiz

## State

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/expert.py status --repo "${CLAUDE_PROJECT_DIR}" || true`

!`python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py status || true`

Script: `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py <status|add FILE|flush>`. It skips duplicates in the deck,
queues cards in `~/.expert/anki-pending.json` when Anki is closed, and syncs to AnkiWeb after adding.

## Arguments (`$ARGUMENTS`, all optional)

| Argument | Effect |
|---|---|
| `<topic or page>` | Only use pages about this topic (match on title, tags, file name). Default: pages updated most recently, plus core pages. |
| `n <count>` | Number of cards. Default 10, max 30. |
| `chat` | Quiz me in the chat instead of Anki. |
| `flush` | Only run `anki.py flush` and report. |
| `es` | In chat mode, explain answers in Spanish too. Cards stay English. |

If the project has no KB, tell me to run `/expert:onboard` first and stop.

## Writing cards

Read the selected pages. Good cards:
- One fact per card; the question makes sense with no context (name the project: "In <slug>, …").
- Mix about 40% **business** (why a feature exists, who uses it, rules, terms from `glossary`) and 60%
  **technical** (where X lives, what calls what, which store holds Y, why a decision was made).
- Prefer understanding over trivia: "why", "what happens when", "which component is responsible for".
- Back: 1–3 short lines. The script adds the source line.
- `source` = the KB page (`projects/<slug>/<page>`) plus the main code path, if any.
- Never put secrets, tokens, personal or customer data on a card.

## Anki mode (default)

1. Write the batch to `~/.expert/quiz-batch.json`:
   `{"deck": "Expert::<slug>", "tags": ["expert", "<slug>"], "cards": [{"front": …, "back": …, "source": …}]}`.
2. Run `anki.py add ~/.expert/quiz-batch.json`.
3. Show me a table (front · back, shortened), then one line: `Added N · duplicates D · queued Q · sync <result>`.
   If Anki is closed, say the cards are queued and will be added on the next `/expert:quiz` or
   `/expert:quiz flush`.

## Chat mode (`chat`, or when Anki is closed and I ask to quiz now)

Ask one question at a time. Wait for my answer, then grade it (correct / partly / wrong), give the right answer
in one or two lines with its source, and move on. At the end, show the score and list the pages to re-read.
