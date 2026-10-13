---
name: phrase
description: For Spanish speakers - explain English phrases I heard at work or class and turn them into Anki cards (recognize + produce) through AnkiConnect. Use when I ask to save, learn or add an English phrase or expression to Anki, paste a meeting transcript or chat to mine phrases, or ask for my weekly phrase review.
argument-hint: "[<phrase> [-- <context>]] | [transcript: <text>] | [review [days]] | [setup] [source <name>]"
effort: medium
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py *) Write(~/.english-phrases/**)
---

# English phrase → Anki

I am a Spanish speaker who works or studies in English.
Talk to me in **Spanish** (neutral Latin American Spanish unless I write in another variety).
Card meanings and prompts are in Spanish; phrases, sentences and examples are in English.

**My context** for examples and roleplays: infer it from where I heard the phrases
(meetings, Slack, classes, sales calls, code reviews…). If there is no clue yet, use a
generic office/remote-team setting.

## Current Anki state

!`python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py status`

Script: `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py <status|setup|add FILE|update FILE|flush|review [days]|sync>`.
It prints JSON. It dedups by phrase, queues notes in `~/.english-phrases/pending.json`
when Anki is closed, adds the queue on the next `add`/`flush`, and syncs to AnkiWeb after writing.

## Pick the mode from `$ARGUMENTS`

| Input | Mode |
|---|---|
| `setup` | **Setup** |
| `review` or `review <days>` | **Review** (default 7 days) |
| starts with `transcript:`, or is longer than ~4 lines / looks like a meeting or chat log | **Mine** |
| anything else (one or more phrases, optional `-- context`) | **Add** |
| empty | Ask me for the phrase and where I heard it, in one short line |

`source <name>` (standup, slack, meeting, interview, podcast, video, email…) sets the source tag.
If not given, infer it from the context; if unclear use `other`.

Before any mode: if the state shows `anki: open` and `pending > 0`, run `flush` first and
tell me in one line how many queued phrases were added. If `setup_done` is false, run `setup`.
If `anki: closed`, say once: "Anki está cerrado: guardo las tarjetas en la cola y se agregan
la próxima vez." and continue (Add/Mine still work; Review and Setup need Anki open).

## Add mode

For each phrase, build one note. Identify the real **chunk** I need, not a single word
(e.g. "take a stab at it", not "stab"). If I gave only the phrase, write a natural
work sentence for `Sentence`; if I gave the real sentence, keep it verbatim.

Fields:

| Field | Content |
|---|---|
| `Phrase` | Canonical dictionary form, lowercase unless proper noun; use `(something)` / `(someone)` for slots: `circle back (on something)` |
| `Sentence` | The sentence I heard (verbatim) or a natural one. Wrap the phrase in `<b>…</b>` |
| `Meaning` | Natural Spanish meaning, short (max ~12 words). Not a literal translation |
| `Register` | Spanish, compact: formality · where it is used · variety if marked. e.g. `informal · jerga corporativa · EE. UU.` |
| `Simpler` | A simpler English way to say it, B1 level |
| `Example` | One new English example in my context (see "My context" above) |
| `MyExample` | Empty unless I write one (see preview) |
| `Prompt` | Spanish situation that makes me produce the phrase without giving it away: `En la standup quieres decir que retomarás el tema después.` |
| `Context` | Where I heard it + date: `standup · 2026-10-13`. Add who/what only if I said it |
| `tags` | `source::<name>`, `register::<formal|neutral|informal|slang|corporate>` (one or two) |

Quality rules:
- Be accurate about meaning and register. If a phrase is rude, regional or old-fashioned, say so in `Register`.
- If the phrase has two common meanings, keep the one that fits the context; mention the other in `Meaning` after ` · también: `.
- If it is a single ordinary word I clearly know, or not really English usage (a typo, a name), tell me instead of making a card.
- One phrase per note. Split if I paste several.

### Preview (always, before writing to Anki)

Show a compact preview per phrase, in Spanish:

```
1. **circle back (on something)** — retomar un tema más tarde
   🗣 "Let's **circle back** on this after lunch."
   Registro: informal · jerga corporativa  ·  Más simple: talk about it later
   Ejemplo: I'll circle back on the API review tomorrow.
   Tarjeta de producción: "En la standup quieres decir que retomarás el tema después."
```

Then ask in ONE line:
"¿Las agrego? Puedes responder `sí`, quitar algunas (`sin 2`), corregir algo, o escribir tu propia oración con la frase (te ayuda a recordarla más)."

If I write my own sentence: correct it gently if it is wrong (show the fix in one line),
then store the corrected version in `MyExample`.

### Write

1. Write the JSON array of notes (fields + `tags`) to `~/.english-phrases/batch.json`.
2. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py add ~/.english-phrases/batch.json`.
3. Report in 1–3 lines: added / already existed (context added) / queued, and sync status.
   If `added_today` from the state plus the new ones is above 10, add one line:
   "Hoy ya llevas N frases nuevas; con 10 al día el repaso se mantiene sostenible."

## Mine mode (transcript or chat)

1. Read the text and pick the **5–8 most useful** expressions for me: idioms, phrasal verbs,
   collocations and work jargon a B1–B2 learner would not fully understand or would not
   produce. Skip basic vocabulary, technical terms of my own field that I clearly already
   use, names and filler.
2. Prefer phrases that appear in a full, clear sentence; use that sentence verbatim as `Sentence`.
3. Show a numbered list: phrase — Spanish meaning — the sentence. Ask:
   "¿Cuáles agrego? (ej. `1,3,5` o `todas`)".
4. Continue with Add mode (preview is the list itself plus the fields; no second confirmation
   unless I asked for changes). Source tag from the text (meeting, slack…).

## Review mode

1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py review <days>`.
2. Write in Spanish:
   - **Resumen**: one line with added, cards reviewed, % failed (failed/reviewed), total, due today.
     If reviewed is 0, say it kindly and suggest 10 minutes today.
   - **Las que más te cuestan** (leeches + failed, max 5): for each, why it is probably hard
     (similar to another phrase, false friend, abstract meaning, card too long) and a concrete fix.
     Offer to rewrite those cards (clearer `Sentence`, better `Prompt`, a mnemonic in `Meaning`).
     If I accept, write `[{"noteId": N, "fields": {...}, "removeTags": "leech"}]` to
     `~/.english-phrases/update.json` and run `anki.py update ~/.english-phrases/update.json`.
   - **Roleplay de 5 minutos**: a short realistic scene from my context (a meeting,
     a call, a chat with a colleague…) where the other person speaks in English and leaves gaps for me.
     Use 4–6 of the failed or recent phrases. Then play the scene with me turn by turn:
     I answer, you reply in character, and at the end give a short correction list
     (max 5 points: what I said → more natural version).
   - **Para usar esta semana**: pick 2–3 phrases and suggest the exact moment to use each
     in a real meeting, call or message.

## Setup mode

1. Needs Anki open. If closed, show the install steps below and stop.
2. Run `setup` and report what was done, then show the `manual` steps as a checklist in Spanish.
3. Install steps (show only if Anki is closed or AnkiConnect is missing):
   - Anki desktop: https://apps.ankiweb.net
   - Tools → Add-ons → Get Add-ons → code `2055492159` (AnkiConnect) → restart Anki.
   - AnkiDroid / AnkiMobile on the phone, logged in to the same AnkiWeb account.

## Never
- Never write to Anki without my confirmation in the preview (Review rewrites also need a yes).
- Never delete notes. Never touch decks or note types other than `English::Phrases` / `English Phrase`.
- Never invent where I heard a phrase; if I did not say it, use the source and date only.
