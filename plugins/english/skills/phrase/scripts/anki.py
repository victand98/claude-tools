#!/usr/bin/env python3
"""Small AnkiConnect client for the /english:phrase skill.

Standard library only. Anki desktop must be open with the AnkiConnect add-on
(code 2055492159). Notes that cannot be added while Anki is closed are queued
in ~/.english-phrases/pending.json and added on the next run.

Usage:
  anki.py status              Connection, pending queue, cards added today
  anki.py setup               Create deck, note type and deck preset (idempotent)
  anki.py add <batch.json>    Add notes (dedup by phrase), then sync
  anki.py flush               Add queued notes, then sync
  anki.py review [days]       JSON with recent failures, leeches and stats
  anki.py sync                Sync with AnkiWeb
"""
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date

URL = os.environ.get("ANKI_CONNECT_URL", "http://127.0.0.1:8765")
DECK = os.environ.get("ENGLISH_PHRASES_DECK", "English::Phrases")
MODEL = "English Phrase"
PRESET = "English Phrases"
NEW_PER_DAY = 10
HOME = os.path.expanduser("~/.english-phrases")
PENDING = os.path.join(HOME, "pending.json")

FIELDS = [
    "Phrase",     # canonical form, e.g. "circle back (on something)"
    "Sentence",   # the real sentence heard, phrase in <b>bold</b>
    "Meaning",    # natural Spanish meaning
    "Register",   # e.g. "informal · corporate"
    "Simpler",    # simpler alternative in English
    "Example",    # new example in a software-work context
    "MyExample",  # my own sentence (optional)
    "Prompt",     # Spanish situation for the production card
    "Context",    # where I heard it (one line per sighting)
]

CSS = """.card { font-family: -apple-system, system-ui, sans-serif; font-size: 20px;
  line-height: 1.45; text-align: left; max-width: 640px; margin: 0 auto; padding: 8px;
  color: #1f2328; background: #fff; }
.nightMode.card, .night_mode .card { color: #e6edf3; background: #1e1e1e; }
.sentence { font-size: 24px; }
.phrase { font-size: 26px; font-weight: 700; }
.meaning { font-size: 22px; margin: 6px 0 12px; }
.label { font-size: 13px; text-transform: uppercase; letter-spacing: .04em; opacity: .6; margin-top: 12px; }
.small { font-size: 17px; }
.hint { font-size: 15px; opacity: .65; }
b { color: #0969da; }
.nightMode b, .night_mode b { color: #58a6ff; }
"""

BACK_DETAILS = """<div class="label">Registro</div><div class="small">{{Register}}</div>
{{#Simpler}}<div class="label">Más simple</div><div class="small">{{Simpler}}</div>{{/Simpler}}
{{#Example}}<div class="label">Ejemplo</div><div class="small">{{Example}}</div>{{/Example}}
{{#MyExample}}<div class="label">Mi ejemplo</div><div class="small">{{MyExample}}</div>{{/MyExample}}
{{#Context}}<div class="label">Dónde lo escuché</div><div class="small hint">{{Context}}</div>{{/Context}}"""

TEMPLATES = [
    {
        "Name": "Recognize",
        "Front": '<div class="sentence">{{Sentence}}</div>\n{{tts en_US:Sentence}}\n'
                 '<div class="hint">¿Qué significa la parte en negrita?</div>',
        "Back": '<div class="sentence">{{Sentence}}</div>\n<hr id=answer>\n'
                '<div class="phrase">{{Phrase}}</div>\n<div class="meaning">{{Meaning}}</div>\n'
                + BACK_DETAILS,
    },
    {
        "Name": "Produce",
        "Front": '<div class="meaning">{{Prompt}}</div>\n'
                 '<div class="hint">¿Cómo lo dirías en inglés?</div>',
        "Back": '<div class="meaning">{{Prompt}}</div>\n<hr id=answer>\n'
                '<div class="phrase">{{Phrase}}</div>\n{{tts en_US:Phrase}}\n'
                '<div class="sentence small">{{Sentence}}</div>\n' + BACK_DETAILS,
    },
]


class AnkiUnavailable(Exception):
    pass


def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            reply = json.load(resp)
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise AnkiUnavailable(str(e))
    if reply.get("error"):
        raise RuntimeError(f"{action}: {reply['error']}")
    return reply.get("result")


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def norm(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\([^)]*\)", "", text)          # drop "(on something)"
    text = re.sub(r"\b(sb|sth|someone|something)\b", "", text)
    text = re.sub(r"[^\w' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_pending():
    try:
        with open(PENDING, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_pending(items):
    os.makedirs(HOME, exist_ok=True)
    if items:
        with open(PENDING, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    elif os.path.exists(PENDING):
        os.remove(PENDING)


def is_ready():
    return MODEL in invoke("modelNames") and DECK in invoke("deckNames")


# ---------------------------------------------------------------- commands

def cmd_status():
    pending = read_pending()
    info = {"anki": "closed", "pending": len(pending), "deck": DECK,
            "new_per_day_target": NEW_PER_DAY}
    try:
        info["ankiconnect_version"] = invoke("version")
        info["anki"] = "open"
        info["setup_done"] = is_ready()
        if info["setup_done"]:
            info["added_today"] = len(invoke("findNotes", query=f'"note:{MODEL}" added:1'))
            info["total_phrases"] = len(invoke("findNotes", query=f'"note:{MODEL}"'))
            info["due_today"] = len(invoke("findCards", query=f'"deck:{DECK}" is:due'))
    except AnkiUnavailable:
        info["hint"] = "Open Anki desktop with AnkiConnect (add-on 2055492159)."
    except RuntimeError as e:
        info["error"] = str(e)
    out(info)


def cmd_setup():
    done = []
    if DECK not in invoke("deckNames"):
        invoke("createDeck", deck=DECK)
        done.append(f"created deck {DECK}")
    if MODEL not in invoke("modelNames"):
        invoke("createModel", modelName=MODEL, inOrderFields=FIELDS, css=CSS,
               isCloze=False, cardTemplates=TEMPLATES)
        done.append(f"created note type {MODEL}")
    else:
        missing = [f for f in FIELDS if f not in invoke("modelFieldNames", modelName=MODEL)]
        for f in missing:
            invoke("modelFieldAdd", modelName=MODEL, fieldName=f)
        invoke("updateModelStyling", model={"name": MODEL, "css": CSS})
        invoke("updateModelTemplates", model={
            "name": MODEL,
            "templates": {t["Name"]: {"Front": t["Front"], "Back": t["Back"]} for t in TEMPLATES}})
        done.append("updated note type templates" + (f" (+fields {missing})" if missing else ""))

    # Own preset so other decks are untouched: 10 new/day, bury siblings.
    try:
        cfg = invoke("getDeckConfig", deck=DECK)
        if cfg.get("name") != PRESET:
            new_id = invoke("cloneDeckConfigId", name=PRESET, cloneFrom=cfg["id"])
            invoke("setDeckConfigId", decks=[DECK], configId=new_id)
            cfg = invoke("getDeckConfig", deck=DECK)
            done.append(f"created preset '{PRESET}'")
        cfg["new"]["perDay"] = NEW_PER_DAY
        cfg["new"]["bury"] = True
        cfg["rev"]["bury"] = True
        invoke("saveDeckConfig", config=cfg)
        done.append(f"preset: {NEW_PER_DAY} new/day, bury siblings on")
    except (RuntimeError, KeyError, TypeError) as e:
        done.append(f"preset not changed ({e}); set it by hand")
    out({"ok": True, "done": done, "manual": [
        f"Deck options of '{DECK}' → FSRS section: turn FSRS on (applies to all decks)",
        f"Same screen, preset '{PRESET}': desired retention 0.90",
        "Lapses → leech action: Tag only → Save",
        "Log in to AnkiWeb (Sync button) so cards reach your phone",
    ]})


def build_note(item):
    fields = {f: (item.get(f) or "").strip() for f in FIELDS}
    if not fields["Phrase"] or not fields["Sentence"] or not fields["Meaning"]:
        raise ValueError(f"Phrase, Sentence and Meaning are required: {item.get('Phrase')!r}")
    tags = sorted(set(item.get("tags", [])) | {f"added::{date.today():%Y-%m}"})
    return {"deckName": DECK, "modelName": MODEL, "fields": fields, "tags": tags,
            "options": {"allowDuplicate": True}}


def add_items(items):
    """Returns per-item results. Duplicates get the new context appended."""
    existing = {}
    ids = invoke("findNotes", query=f'"note:{MODEL}"')
    for n in invoke("notesInfo", notes=ids) if ids else []:
        existing[norm(n["fields"]["Phrase"]["value"])] = n

    results = []
    for item in items:
        note = build_note(item)
        key = norm(note["fields"]["Phrase"])
        if key in existing:
            old = existing[key]
            ctx_old = old["fields"]["Context"]["value"]
            ctx_new = note["fields"]["Context"]
            updates = {}
            if ctx_new and norm(ctx_new) not in norm(ctx_old):
                updates["Context"] = f"{ctx_old}<br>{ctx_new}" if ctx_old else ctx_new
            if note["fields"]["MyExample"] and not old["fields"]["MyExample"]["value"]:
                updates["MyExample"] = note["fields"]["MyExample"]
            if updates:
                invoke("updateNoteFields", note={"id": old["noteId"], "fields": updates})
            if note["tags"]:
                invoke("addTags", notes=[old["noteId"]], tags=" ".join(note["tags"]))
            results.append({"phrase": note["fields"]["Phrase"], "status": "exists",
                            "updated": list(updates), "noteId": old["noteId"]})
        else:
            nid = invoke("addNote", note=note)
            existing[key] = {"noteId": nid, "fields": {f: {"value": v} for f, v in note["fields"].items()}}
            results.append({"phrase": note["fields"]["Phrase"], "status": "added", "noteId": nid})
    return results


def try_sync():
    try:
        invoke("sync")
        return "ok"
    except RuntimeError as e:
        return f"failed: {e}"


def cmd_add(path):
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = [items]
    for it in items:
        build_note(it)  # validate before touching Anki or the queue
    queue = read_pending()
    try:
        if not is_ready():
            cmd_setup_quiet()
        results = add_items(queue + items)
        write_pending([])
        out({"anki": "open", "results": results, "sync": try_sync(),
             "flushed_from_queue": len(queue)})
    except AnkiUnavailable:
        write_pending(queue + items)
        out({"anki": "closed", "queued": len(items), "pending_total": len(queue) + len(items),
             "hint": "Saved to the queue. Open Anki and run /english:phrase again to add them."})
    except RuntimeError:
        # Keep everything queued; dedup makes a retry safe even after a partial add.
        write_pending(queue + items)
        raise


def cmd_setup_quiet():
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_setup()


def cmd_flush():
    queue = read_pending()
    if not queue:
        out({"pending": 0})
        return
    try:
        if not is_ready():
            cmd_setup_quiet()
        results = add_items(queue)
        write_pending([])
        out({"results": results, "sync": try_sync()})
    except AnkiUnavailable:
        out({"anki": "closed", "pending": len(queue)})


def phrases(query, limit=40):
    ids = invoke("findNotes", query=query)[:limit]
    notes = invoke("notesInfo", notes=ids) if ids else []
    return [{"phrase": n["fields"]["Phrase"]["value"],
             "meaning": n["fields"]["Meaning"]["value"],
             "sentence": n["fields"]["Sentence"]["value"],
             "tags": n["tags"], "noteId": n["noteId"]} for n in notes]


def cmd_review(days="7"):
    d = int(days)
    base = f'"note:{MODEL}"'
    lapses = {}
    cids = invoke("findCards", query=f"{base} prop:lapses>=3")
    for c in invoke("cardsInfo", cards=cids) if cids else []:
        lapses[c["note"]] = max(lapses.get(c["note"], 0), c.get("lapses", 0))
    leeches = phrases(f"{base} (tag:leech OR prop:lapses>=3)")
    for p in leeches:
        p["lapses"] = lapses.get(p["noteId"])
    out({
        "days": d,
        "stats": {
            "added": len(invoke("findNotes", query=f"{base} added:{d}")),
            "cards_reviewed": len(invoke("findCards", query=f"{base} rated:{d}")),
            "cards_failed": len(invoke("findCards", query=f"{base} rated:{d}:1")),
            "total_phrases": len(invoke("findNotes", query=base)),
            "due_today": len(invoke("findCards", query=f'"deck:{DECK}" is:due')),
        },
        "failed_recently": phrases(f"{base} rated:{d}:1"),
        "leeches": leeches,
        "added_recently": phrases(f"{base} added:{d}"),
    })


def cmd_update(path):
    """Rewrite fields of existing notes: [{"noteId": 1, "fields": {...}, "removeTags": "leech"}]"""
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        items = json.load(f)
    done = []
    for it in items:
        fields = {k: v for k, v in it.get("fields", {}).items() if k in FIELDS}
        if fields:
            invoke("updateNoteFields", note={"id": it["noteId"], "fields": fields})
        if it.get("removeTags"):
            invoke("removeTags", notes=[it["noteId"]], tags=it["removeTags"])
        done.append(it["noteId"])
    out({"updated": done, "sync": try_sync()})


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    try:
        if cmd == "status":
            cmd_status()
        elif cmd == "setup":
            cmd_setup()
        elif cmd == "add" and len(argv) > 2:
            cmd_add(argv[2])
        elif cmd == "update" and len(argv) > 2:
            cmd_update(argv[2])
        elif cmd == "flush":
            cmd_flush()
        elif cmd == "review":
            cmd_review(*argv[2:3])
        elif cmd == "sync":
            out({"sync": try_sync()})
        else:
            print(__doc__)
            return 2
    except AnkiUnavailable as e:
        out({"anki": "closed", "error": str(e),
             "hint": "Open Anki desktop with AnkiConnect (add-on 2055492159)."})
        return 1
    except (RuntimeError, ValueError) as e:
        out({"error": str(e)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
