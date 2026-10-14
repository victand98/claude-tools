---
name: phrase
description: For Spanish speakers - explain English phrases I heard at work or class and turn them into English-only Anki cards (recognize + produce, with audio) through AnkiConnect. Use when I ask to save, learn or add an English phrase or expression to Anki, paste a meeting transcript or chat to mine phrases, or ask for my weekly phrase review.
argument-hint: "[<phrase> [-- <context>]] [image <path|url>] | [transcript: <text>] | [review [days]] | [setup] [source <name>]"
effort: medium
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py *) Write(~/.english-phrases/**)
---

# English phrase → Anki

I am a Spanish speaker who works or studies in English.

- **Chat with me in Spanish** (neutral Latin American Spanish unless I write in another variety):
  explanations, questions, previews, corrections.
- **Everything that goes on the cards is in English. No Spanish on the cards**, ever.
  Definitions use simple English, like a learner's dictionary (Cambridge / Oxford Learner's style).

**My context** for examples and roleplays: infer it from where I heard the phrases
(meetings, Slack, classes, sales calls, code reviews…). If there is no clue yet, use a
generic office/remote-team setting.

## Current Anki state

!`python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py status`

Script: `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py <status|setup|add FILE|update FILE|list|shared|flush|review [days]|sync>`.
It prints JSON. It dedups by phrase, generates MP3 audio with `edge-tts` (two US voices, alternating),
stores images, queues notes in `~/.english-phrases/pending.json` when Anki is closed, adds the queue
on the next `add`/`flush`, and syncs to AnkiWeb after writing.

## Pick the mode from `$ARGUMENTS`

| Input | Mode |
|---|---|
| `setup` | **Setup** |
| `review` or `review <days>` | **Review** (default 7 days) |
| starts with `transcript:`, or is longer than ~4 lines / looks like a meeting or chat log | **Mine** |
| anything else (one or more phrases, optional `-- context`, optional `image <path or url>`) | **Add** |
| empty | Ask me for the phrase and where I heard it, in one short line |

`source <name>` (standup, slack, meeting, interview, podcast, video, email…) sets the source tag.
If not given, infer it from the context; if unclear use `other`.

Before any mode:
- If the state shows `anki: open` and `pending > 0`, run `flush` first and tell me in one line how many queued phrases were added.
- If `setup_done` is false, run **Setup** (it also upgrades old cards).
- If `audio_engine` is `missing`, tell me once, in Spanish, to install it and continue without audio:
  `pipx install edge-tts` (or `pip install --user edge-tts`; on Windows `py -m pip install edge-tts`).
- If `shared_sentences` > 0, run **Fix shared sentences** (below) before the requested mode, after asking me in one line.
- If `anki: closed`, say once: "Anki está cerrado: guardo las tarjetas en la cola y se agregan
  la próxima vez." and continue (Add/Mine still work; Review and Setup need Anki open).

## Add mode

For each phrase, build one note. Identify the real **chunk** I need, not a single word
(e.g. "take a stab at it", not "stab"). If I gave only the phrase, write a natural
sentence for `Sentence`; if I gave the real sentence, keep it verbatim.

Fields (all in **English**):

| Field | Content |
|---|---|
| `Phrase` | Canonical dictionary form, lowercase unless proper noun; use `(something)` / `(someone)` for slots: `circle back (on something)` |
| `Sentence` | The sentence I heard (verbatim) or a natural one. Wrap the phrase in `<b>…</b>` |
| `Definition` | Learner's-dictionary definition, max ~15 words, using common words (B1 level). Must not reuse the key words of the phrase. Not a translation |
| `Register` | Compact: formality · where it is used · variety if marked. e.g. `informal · business jargon · mostly US` |
| `Simpler` | A simpler English way to say the same thing |
| `Example` | One new example in my context (see "My context" above) |
| `MyExample` | Empty unless I write one (see preview) |
| `Prompt` | Production cue in English: a short situation + what I want to express, **without any of the phrase's key words**, so I must recall the phrase. e.g. `In a meeting, you want to say you'll come back to this topic later.` |
| `Context` | Where I heard it + date: `standup · 2026-10-13`. Add who/what only if I said it |
| `tags` | `source::<name>`, `register::<formal|neutral|informal|slang|corporate>` (one or two) |
| `image` | Optional, see Images. A local path or an http(s) URL; the script stores it |

### One target per sentence (important)

Each card must test **one** thing, and each sentence must belong to **one** card only.
Reusing a sentence for several phrases makes me memorize the sentence instead of the phrase,
and similar cards interfere with each other (the main cause of forgetting in spaced repetition).
Seeing a phrase in **different** sentences also helps learning more than repeating the same one.

- A heard sentence is used verbatim for **only one** phrase: the most useful one in it.
- Every other phrase from that same sentence gets a **new, natural sentence** in my context,
  and the heard sentence goes in its `Context` as a quote: `meeting · 2026-10-13 — "We need to touch base and get the ball rolling."`
- In `Sentence`, only the target phrase is bold, and the rest of the sentence should be easy (no other new expressions).
- `Example` must be a different sentence from `Sentence`, ideally in a different situation.
- The script enforces this: a phrase whose sentence is already used by another note returns
  `status: "sentence_conflict"` and is **not** added. When that happens, write a new sentence for it
  (keep the heard one in `Context`), show me the change in one line, and add it again — no extra confirmation needed.
- If the phrase already exists and I heard it in a new sentence, just add it again: the script appends the
  new sentence to `Context` (more contexts = better learning).

Quality rules:
- Be accurate about meaning and register. If a phrase is rude, regional or old-fashioned, say so in `Register`.
- If the phrase has two common meanings, keep the one that fits the context; add the other to `Definition` after ` · Also: `.
- If it is a single ordinary word I clearly know, or not really English usage (a typo, a name), tell me instead of making a card.
- One phrase per note. Split if I paste several.

### Images (optional, only when they help)

Research shows pictures help remember the **meaning** of concrete or literal expressions,
but they add little for abstract phrases and can even hurt recall of the **exact words**
of longer expressions. So:
- Add an image only when I pass `image <path|url>` (e.g. a screenshot of the scene where I heard it), or
  when I explicitly ask for one.
- If a phrase is concrete/visual (e.g. "on the same page", "ballpark figure") and I gave no image,
  you may suggest in the preview: "Esta frase es visual; si quieres, pásame una imagen o captura con `image <ruta>`."
  Never suggest it for abstract phrases.
- Never search the web for images on your own. The image goes on the back of the cards.

### Preview (always, before writing to Anki)

Explain in Spanish, show card content in English:

```
1. **circle back (on something)** — to return to a topic later
   🗣 "Let's **circle back** on this after lunch."
   Register: informal · business jargon  ·  Simpler: talk about it later
   Example: I'll circle back on the API review tomorrow.
   Produce card: "In a meeting, you want to say you'll come back to this topic later."
   💬 (es) Equivale a "retomar el tema después". Muy común en reuniones de trabajo en EE. UU.
```

The `💬 (es)` line is only for the chat, to make sure I understood. It is **never** stored on the card.

Then ask in ONE line:
"¿Las agrego? Puedes responder `sí`, quitar algunas (`sin 2`), corregir algo, o escribir tu propia oración en inglés con la frase (te ayuda a recordarla más)."

If I write my own sentence: correct it gently if it is wrong (show the fix in one line),
then store the corrected version in `MyExample`.

### Write

1. Write the JSON array of notes (fields + `tags` + optional `image`) to `~/.english-phrases/batch.json`.
2. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py add ~/.english-phrases/batch.json`.
3. Report in 1–3 lines (Spanish): added / already existed (context added) / queued, audio yes/no, sync status.
   If `added_today` from the state plus the new ones is above 10, add one line:
   "Hoy ya llevas N frases nuevas; con 10 al día el repaso se mantiene sostenible."

## Mine mode (transcript or chat)

1. Read the text and pick the **5–8 most useful** expressions for me: idioms, phrasal verbs,
   collocations and work jargon a B1–B2 learner would not fully understand or would not
   produce. Skip basic vocabulary, technical terms of my own field that I clearly already
   use, names and filler.
2. Prefer phrases that appear in a full, clear sentence. Apply **One target per sentence**: if two selected
   phrases come from the same sentence, use it verbatim for one and write a new sentence for the other.
3. Show a numbered list: phrase — English definition — the sentence (and a short Spanish hint in the chat only). Ask:
   "¿Cuáles agrego? (ej. `1,3,5` o `todas`)".
4. Continue with Add mode (preview is the list itself plus the fields; no second confirmation
   unless I asked for changes). Source tag from the text (meeting, slack…).

## Fix shared sentences

1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py shared`. Each group is a set of notes using the same sentence.
2. In each group keep the sentence for the most useful phrase. For every other note, write a new natural
   sentence (bold only the target, easy surrounding words) and move the old sentence into `Context` as a quote.
3. Show me the proposal (Spanish explanation, English card content), max 10 notes per batch. After my yes,
   write `[{"noteId": N, "fields": {"Sentence": "...", "Context": "..."}, "audio": true}]` to
   `~/.english-phrases/update.json` and run `anki.py update ~/.english-phrases/update.json`.
   Review progress is kept (the cards are edited, not recreated).

## Review mode

1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/anki.py review <days>`.
2. Write in Spanish:
   - **Resumen**: one line with added, cards reviewed, % failed (failed/reviewed), total, due today.
     If reviewed is 0, say it kindly and suggest 10 minutes today.
   - **Las que más te cuestan** (leeches + failed, max 5): for each, why it is probably hard
     (similar to another phrase, false friend, abstract meaning, card too long) and a concrete fix.
     Offer to rewrite those cards in English (clearer `Sentence`, better `Prompt`, simpler `Definition`).
     If I accept, write `[{"noteId": N, "fields": {...}, "audio": true, "removeTags": "leech"}]` to
     `~/.english-phrases/update.json` and run `anki.py update ~/.english-phrases/update.json`
     (`audio: true` only if `Sentence` or `Phrase` changed).
   - **Roleplay de 5 minutos** (in English): a short realistic scene from my context (a meeting,
     a call, a chat with a colleague…) where the other person speaks and leaves gaps for me.
     Use 4–6 of the failed or recent phrases. Then play the scene with me turn by turn:
     I answer, you reply in character, and at the end give a short correction list in Spanish
     (max 5 points: what I said → more natural version).
   - **Para usar esta semana**: pick 2–3 phrases and suggest the exact moment to use each
     in a real meeting, call or message.

## Setup mode

1. Needs Anki open. If closed, show the install steps below and stop.
2. Run `setup` and report what was done (in Spanish), then show the `manual` steps as a checklist in Spanish.
   Desired retention is typed as **90** (the field is a percentage; typing 0.90 sets it to the minimum).
3. If `shared_sentences` > 0 in the status, run **Fix shared sentences**.
4. **Upgrade old cards**: if `notes` > 0, run `list` and look for notes whose `Definition`, `Register`
   or `Prompt` are in Spanish, or that have `has_audio: false`. Propose English versions
   (same preview format, max 10 per batch) and, after my yes, write them as
   `[{"noteId": N, "fields": {...}, "audio": true}]` to `~/.english-phrases/update.json` and run `update`.
5. Install steps (show only if Anki is closed, AnkiConnect is missing, or audio is missing):
   - Anki desktop: https://apps.ankiweb.net
   - Tools → Add-ons → Get Add-ons → code `2055492159` (AnkiConnect) → restart Anki.
   - Audio: `pipx install edge-tts` (or `pip install --user edge-tts`). Needs internet when creating cards;
     the MP3 files then sync and play everywhere, including the phone.
   - AnkiDroid / AnkiMobile on the phone, logged in to the same AnkiWeb account.

## Never
- Never put Spanish on a card.
- Never use the same sentence on two notes.
- Never write to Anki without my confirmation in the preview (Review and upgrade rewrites also need a yes).
- Never delete notes. Never touch decks or note types other than `English::Phrases` / `English Phrase`.
- Never invent where I heard a phrase; if I did not say it, use the source and date only.
