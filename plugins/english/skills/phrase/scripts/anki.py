#!/usr/bin/env python3
"""Small AnkiConnect client for the /english:phrase skill.

Standard library only (audio needs the `edge-tts` command, optional).
Anki desktop must be open with the AnkiConnect add-on (code 2055492159).
Notes that cannot be added while Anki is closed are queued in
~/.english-phrases/pending.json and added on the next run.

Usage:
  anki.py status              Connection, audio engine, queue, cards added today
  anki.py setup               Create/upgrade deck, note type and deck preset (idempotent)
  anki.py add <batch.json>    Add notes (dedup by phrase, audio, image), then sync
  anki.py update <file.json>  Rewrite fields / regenerate audio of existing notes, then sync
  anki.py list                All phrase notes (to upgrade old cards)
  anki.py flush               Add queued notes, then sync
  anki.py review [days]       JSON with recent failures, leeches and stats
  anki.py sync                Sync with AnkiWeb
"""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.request
from datetime import date

URL = os.environ.get("ANKI_CONNECT_URL", "http://127.0.0.1:8765")
DECK = os.environ.get("ENGLISH_PHRASES_DECK", "English::Phrases")
VOICES = [v.strip() for v in os.environ.get(
    "ENGLISH_PHRASES_VOICES", "en-US-AriaNeural,en-US-GuyNeural").split(",") if v.strip()]
MODEL = "English Phrase"
PRESET = "English Phrases"
NEW_PER_DAY = 10
HOME = os.path.expanduser("~/.english-phrases")
PENDING = os.path.join(HOME, "pending.json")

# Everything on the cards is English (monolingual cards).
FIELDS = [
    "Phrase",          # canonical form, e.g. "circle back (on something)"
    "Sentence",        # the real sentence heard, phrase in <b>bold</b>
    "Definition",      # simple learner's-dictionary definition in English
    "Register",        # e.g. "informal · business jargon · US"
    "Simpler",         # simpler alternative in English
    "Example",         # new example in my context
    "MyExample",       # my own sentence (optional)
    "Prompt",          # English cue for the production card (no words of the phrase)
    "Context",         # where I heard it (one line per sighting)
    "Image",           # optional <img>, only when it helps (screenshot, concrete scene)
    "SentenceAudio",   # [sound:...] generated MP3
    "PhraseAudio",     # [sound:...] generated MP3
]
RENAMES = {"Meaning": "Definition"}  # v1 → v2

CSS = """.card { font-family: -apple-system, system-ui, sans-serif; font-size: 20px;
  line-height: 1.45; text-align: left; max-width: 640px; margin: 0 auto; padding: 8px;
  color: #1f2328; background: #fff; }
.nightMode.card, .night_mode .card { color: #e6edf3; background: #1e1e1e; }
.sentence { font-size: 24px; }
.phrase { font-size: 26px; font-weight: 700; }
.definition { font-size: 21px; margin: 6px 0 12px; }
.prompt { font-size: 21px; }
.label { font-size: 13px; text-transform: uppercase; letter-spacing: .04em; opacity: .6; margin-top: 12px; }
.small { font-size: 17px; }
.hint { font-size: 15px; opacity: .65; }
.image img { max-width: 100%; max-height: 260px; border-radius: 8px; margin-top: 10px; }
b { color: #0969da; }
.nightMode b, .night_mode b { color: #58a6ff; }
"""

BACK_DETAILS = """{{#Image}}<div class="image">{{Image}}</div>{{/Image}}
<div class="label">Register</div><div class="small">{{Register}}</div>
{{#Simpler}}<div class="label">Simpler</div><div class="small">{{Simpler}}</div>{{/Simpler}}
{{#Example}}<div class="label">Example</div><div class="small">{{Example}}</div>{{/Example}}
{{#MyExample}}<div class="label">My example</div><div class="small">{{MyExample}}</div>{{/MyExample}}
{{#Context}}<div class="label">Heard in</div><div class="small hint">{{Context}}</div>{{/Context}}"""

TEMPLATES = [
    {
        "Name": "Recognize",
        "Front": '<div class="sentence">{{Sentence}}</div>\n{{SentenceAudio}}\n'
                 '<div class="hint">What does the bold part mean?</div>',
        "Back": '<div class="sentence">{{Sentence}}</div>\n<hr id=answer>\n'
                '<div class="phrase">{{Phrase}}</div>\n{{PhraseAudio}}\n'
                '<div class="definition">{{Definition}}</div>\n' + BACK_DETAILS,
    },
    {
        "Name": "Produce",
        "Front": '<div class="prompt">{{Prompt}}</div>\n'
                 '<div class="hint">Say it out loud, then check.</div>',
        "Back": '<div class="prompt">{{Prompt}}</div>\n<hr id=answer>\n'
                '<div class="phrase">{{Phrase}}</div>\n{{PhraseAudio}}\n'
                '<div class="sentence small">{{Sentence}}</div>\n{{SentenceAudio}}\n'
                '<div class="definition small">{{Definition}}</div>\n' + BACK_DETAILS,
    },
]


class AnkiUnavailable(Exception):
    pass


def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            reply = json.load(resp)
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise AnkiUnavailable(str(e))
    if reply.get("error"):
        raise RuntimeError(f"{action}: {reply['error']}")
    return reply.get("result")


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def strip_html(text):
    text = re.sub(r"<br\s*/?>", " ", text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def norm(text):
    text = unicodedata.normalize("NFKC", strip_html(text)).lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\([^)]*\)", "", text)          # drop "(on something)"
    text = re.sub(r"\b(sb|sth|someone|something)\b", "", text)
    text = re.sub(r"[^\w' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------- audio

def tts_command():
    exe = shutil.which("edge-tts")
    if not exe:  # pipx installs here; it may not be on PATH yet
        local = os.path.expanduser("~/.local/bin/edge-tts")
        exe = local if os.access(local, os.X_OK) else None
    if exe:
        return [exe]
    try:
        import edge_tts  # noqa: F401
        return [sys.executable, "-m", "edge_tts"]
    except ImportError:
        return None


def make_audio(text, key):
    """Returns '[sound:file.mp3]' or '' (never raises)."""
    text = strip_html(text)
    cmd = tts_command()
    if not text or not cmd:
        return ""
    voice = VOICES[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(VOICES)] if VOICES else "en-US-AriaNeural"
    fname = "ephr_" + hashlib.md5(f"{voice}|{text}".encode()).hexdigest()[:16] + ".mp3"
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, fname)
        try:
            subprocess.run(cmd + ["--voice", voice, "--text", text, "--write-media", path],
                           check=True, capture_output=True, timeout=60)
            with open(path, "rb") as f:
                raw = f.read()
        except (subprocess.SubprocessError, OSError):
            return ""
        if len(raw) < 1000:  # failed or truncated download
            return ""
        data = base64.b64encode(raw).decode()
    invoke("storeMediaFile", filename=fname, data=data)
    return f"[sound:{fname}]"


def add_audio(fields):
    """Fills SentenceAudio / PhraseAudio if empty. Returns True if audio engine worked."""
    ok = True
    phrase_text = re.sub(r"\(([^)]*)\)", "", strip_html(fields["Phrase"])).strip()
    for src, dst, text in (("Sentence", "SentenceAudio", fields["Sentence"]),
                           ("Phrase", "PhraseAudio", phrase_text)):
        if not fields.get(dst) and text:
            fields[dst] = make_audio(text, fields["Phrase"])
            ok = ok and bool(fields[dst])
    return ok


# ---------------------------------------------------------------- image

def add_image(fields, image):
    """image: local path or http(s) URL. Stores it and sets the Image field."""
    if not image or fields.get("Image"):
        return
    ext = os.path.splitext(image.split("?")[0])[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"
    fname = "ephr_img_" + hashlib.md5(image.encode()).hexdigest()[:16] + ext
    if re.match(r"https?://", image):
        invoke("storeMediaFile", filename=fname, url=image)
    else:
        with open(os.path.expanduser(image), "rb") as f:
            invoke("storeMediaFile", filename=fname, data=base64.b64encode(f.read()).decode())
    fields["Image"] = f'<img src="{fname}">'


# ---------------------------------------------------------------- queue

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
    if MODEL not in invoke("modelNames") or DECK not in invoke("deckNames"):
        return False
    return set(FIELDS) <= set(invoke("modelFieldNames", modelName=MODEL))


# ---------------------------------------------------------------- commands

def cmd_status():
    pending = read_pending()
    info = {"anki": "closed", "pending": len(pending), "deck": DECK,
            "audio_engine": "edge-tts" if tts_command() else "missing",
            "new_per_day_target": NEW_PER_DAY}
    if not tts_command():
        info["audio_hint"] = "Install edge-tts for audio: pipx install edge-tts (or: pip install --user edge-tts)"
    try:
        info["ankiconnect_version"] = invoke("version")
        info["anki"] = "open"
        info["setup_done"] = is_ready()
        if MODEL in invoke("modelNames"):
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
        have = invoke("modelFieldNames", modelName=MODEL)
        for old, new in RENAMES.items():
            if old in have and new not in have:
                invoke("modelFieldRename", modelName=MODEL, oldFieldName=old, newFieldName=new)
                done.append(f"renamed field {old} → {new}")
        have = invoke("modelFieldNames", modelName=MODEL)
        missing = [f for f in FIELDS if f not in have]
        for f in missing:
            invoke("modelFieldAdd", modelName=MODEL, fieldName=f)
        if missing:
            done.append(f"added fields {missing}")
        invoke("updateModelStyling", model={"name": MODEL, "css": CSS})
        invoke("updateModelTemplates", model={
            "name": MODEL,
            "templates": {t["Name"]: {"Front": t["Front"], "Back": t["Back"]} for t in TEMPLATES}})
        done.append("updated card templates (English only, MP3 audio)")

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

    total = len(invoke("findNotes", query=f'"note:{MODEL}"'))
    no_audio = len(invoke("findNotes", query=f'"note:{MODEL}" SentenceAudio:'))
    out({"ok": True, "done": done, "notes": total, "notes_without_audio": no_audio,
         "audio_engine": "edge-tts" if tts_command() else "missing",
         "manual": [
             f"Deck options of '{DECK}' → FSRS section: turn FSRS on (applies to all decks)",
             f"Same screen, preset '{PRESET}': desired retention 90 (it is a percentage)",
             "Lapses → leech action: Tag only → Save",
             "Log in to AnkiWeb (Sync button) so cards reach your phone",
         ]})


def build_note(item):
    fields = {f: (item.get(f) or "").strip() for f in FIELDS}
    if not fields["Phrase"] or not fields["Sentence"] or not fields["Definition"]:
        raise ValueError(f"Phrase, Sentence and Definition are required: {item.get('Phrase')!r}")
    tags = sorted(set(item.get("tags", [])) | {f"added::{date.today():%Y-%m}"})
    return {"deckName": DECK, "modelName": MODEL, "fields": fields, "tags": tags,
            "options": {"allowDuplicate": True}}


def add_items(items):
    """Returns per-item results. Duplicates get the new context appended."""
    existing = {}
    ids = invoke("findNotes", query=f'"note:{MODEL}"')
    for n in invoke("notesInfo", notes=ids) if ids else []:
        existing[norm(n["fields"]["Phrase"]["value"])] = n

    results, audio_ok = [], True
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
            if item.get("image") and not old["fields"].get("Image", {}).get("value"):
                tmp = {"Image": ""}
                add_image(tmp, item["image"])
                updates["Image"] = tmp["Image"]
            if updates:
                invoke("updateNoteFields", note={"id": old["noteId"], "fields": updates})
            invoke("addTags", notes=[old["noteId"]], tags=" ".join(note["tags"]))
            results.append({"phrase": note["fields"]["Phrase"], "status": "exists",
                            "updated": list(updates), "noteId": old["noteId"]})
        else:
            audio_ok = add_audio(note["fields"]) and audio_ok
            add_image(note["fields"], item.get("image"))
            nid = invoke("addNote", note=note)
            existing[key] = {"noteId": nid, "fields": {f: {"value": v} for f, v in note["fields"].items()}}
            results.append({"phrase": note["fields"]["Phrase"], "status": "added", "noteId": nid,
                            "audio": bool(note["fields"]["SentenceAudio"]),
                            "image": bool(note["fields"]["Image"])})
    return results, audio_ok


def try_sync():
    try:
        invoke("sync")
        return "ok"
    except RuntimeError as e:
        return f"failed: {e}"


def ensure_ready():
    if not is_ready():
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_setup()


def report(results, audio_ok, extra=None):
    res = {"anki": "open", "results": results, "sync": try_sync()}
    if not audio_ok:
        res["audio_hint"] = ("Audio not generated. Install edge-tts (pipx install edge-tts) and check "
                             "your internet, then run: anki.py update with {\"noteId\": N, \"audio\": true}")
    res.update(extra or {})
    out(res)


def cmd_add(path):
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = [items]
    for it in items:
        build_note(it)  # validate before touching Anki or the queue
    queue = read_pending()
    try:
        ensure_ready()
        results, audio_ok = add_items(queue + items)
        write_pending([])
        report(results, audio_ok, {"flushed_from_queue": len(queue)})
    except AnkiUnavailable:
        write_pending(queue + items)
        out({"anki": "closed", "queued": len(items), "pending_total": len(queue) + len(items),
             "hint": "Saved to the queue. Open Anki and run /english:phrase again to add them."})
    except RuntimeError:
        write_pending(queue + items)  # dedup makes a retry safe
        raise


def cmd_flush():
    queue = read_pending()
    if not queue:
        out({"pending": 0})
        return
    try:
        ensure_ready()
        results, audio_ok = add_items(queue)
        write_pending([])
        report(results, audio_ok)
    except AnkiUnavailable:
        out({"anki": "closed", "pending": len(queue)})


def notes_brief(query, limit=None):
    ids = invoke("findNotes", query=query)
    ids = ids[:limit] if limit else ids
    notes = invoke("notesInfo", notes=ids) if ids else []
    return [{"noteId": n["noteId"], "tags": n["tags"],
             **{k: n["fields"][k]["value"] for k in FIELDS if k in n["fields"]
                and k not in ("SentenceAudio", "PhraseAudio", "Image")},
             "has_audio": bool(n["fields"].get("SentenceAudio", {}).get("value")),
             "has_image": bool(n["fields"].get("Image", {}).get("value"))} for n in notes]


def cmd_list():
    ensure_ready()
    out(notes_brief(f'"note:{MODEL}"'))


def cmd_review(days="7"):
    d = int(days)
    base = f'"note:{MODEL}"'
    lapses = {}
    cids = invoke("findCards", query=f"{base} prop:lapses>=3")
    for c in invoke("cardsInfo", cards=cids) if cids else []:
        lapses[c["note"]] = max(lapses.get(c["note"], 0), c.get("lapses", 0))
    leeches = notes_brief(f"{base} (tag:leech OR prop:lapses>=3)", 40)
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
        "failed_recently": notes_brief(f"{base} rated:{d}:1", 40),
        "leeches": leeches,
        "added_recently": notes_brief(f"{base} added:{d}", 40),
    })


def cmd_update(path):
    """[{"noteId": 1, "fields": {...}, "audio": true, "image": "path|url", "removeTags": "leech"}]
    audio: true regenerates both audio files from the (new) Sentence/Phrase."""
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        items = json.load(f)
    ensure_ready()
    done, audio_ok = [], True
    for it in items:
        nid = it["noteId"]
        fields = {k: v for k, v in it.get("fields", {}).items() if k in FIELDS}
        if it.get("audio"):
            cur = invoke("notesInfo", notes=[nid])[0]["fields"]
            merged = {k: cur.get(k, {}).get("value", "") for k in FIELDS}
            merged.update(fields)
            merged["SentenceAudio"] = merged["PhraseAudio"] = ""
            audio_ok = add_audio(merged) and audio_ok
            fields["SentenceAudio"], fields["PhraseAudio"] = merged["SentenceAudio"], merged["PhraseAudio"]
        if it.get("image"):
            tmp = {"Image": ""}
            add_image(tmp, it["image"])
            fields["Image"] = tmp["Image"]
        if fields:
            invoke("updateNoteFields", note={"id": nid, "fields": fields})
        if it.get("removeTags"):
            invoke("removeTags", notes=[nid], tags=it["removeTags"])
        done.append(nid)
    res = {"updated": done, "sync": try_sync()}
    if not audio_ok:
        res["audio_hint"] = "Audio not generated. Install edge-tts (pipx install edge-tts) and check your internet."
    out(res)


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
        elif cmd == "list":
            cmd_list()
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
    except (RuntimeError, ValueError, OSError) as e:
        out({"error": str(e)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
