#!/usr/bin/env python3
"""Small AnkiConnect client for the /expert:quiz skill.

Standard library only. Anki desktop must be open with the AnkiConnect add-on
(code 2055492159). Cards that cannot be added while Anki is closed are queued in
~/.expert/anki-pending.json and added on the next `add` or `flush`.

Usage:
  anki.py status              Connection and queue size
  anki.py add <batch.json>    Add cards (skips duplicates in the deck), then sync
  anki.py flush               Add queued cards, then sync

batch.json: {"deck": "Expert::<slug>", "tags": ["expert", "<slug>"],
             "cards": [{"front": "...", "back": "...", "source": "path or URL"}]}
"""
import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("ANKI_CONNECT_URL", "http://127.0.0.1:8765")
HOME = os.path.expanduser("~/.expert")
PENDING = os.path.join(HOME, "anki-pending.json")
BASIC_FIELDS = ("Front", "Back")


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


def read_pending():
    try:
        with open(PENDING, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_pending(batches):
    os.makedirs(HOME, exist_ok=True)
    if batches:
        with open(PENDING, "w", encoding="utf-8") as f:
            json.dump(batches, f, ensure_ascii=False, indent=2)
    elif os.path.exists(PENDING):
        os.remove(PENDING)


def basic_model():
    """The built-in Basic note type, found by its fields so a localized name still works."""
    names = invoke("modelNames")
    if "Basic" in names:
        return "Basic"
    for name in names:
        if tuple(invoke("modelFieldNames", modelName=name)) == BASIC_FIELDS:
            return name
    raise RuntimeError("no note type with exactly the fields Front and Back (Anki's Basic)")


def html(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
                       .replace("\n", "<br>")


def build_notes(batch, model):
    notes = []
    for card in batch["cards"]:
        back = html(card["back"])
        if card.get("source"):
            back += f'<br><br><small style="opacity:.6">{html(card["source"])}</small>'
        notes.append({"deckName": batch["deck"], "modelName": model,
                      "fields": {"Front": html(card["front"]), "Back": back},
                      "tags": batch.get("tags", []),
                      "options": {"allowDuplicate": False, "duplicateScope": "deck"}})
    return notes


def add_batch(batch):
    model = basic_model()
    if batch["deck"] not in invoke("deckNames"):
        invoke("createDeck", deck=batch["deck"])
    notes = build_notes(batch, model)
    ok = invoke("canAddNotes", notes=notes)
    fresh = [n for n, can in zip(notes, ok) if can]
    if fresh:
        invoke("addNotes", notes=fresh)
    return {"deck": batch["deck"], "added": len(fresh), "duplicates": len(notes) - len(fresh)}


def try_sync():
    try:
        invoke("sync")
        return "ok"
    except (RuntimeError, AnkiUnavailable) as e:
        return f"failed: {e}"


def cmd_status():
    info = {"anki": "closed", "pending_batches": len(read_pending())}
    try:
        info["anki"] = f"open (AnkiConnect v{invoke('version')})"
    except AnkiUnavailable:
        info["hint"] = "Open Anki desktop with AnkiConnect (add-on 2055492159)."
    out(info)


def flush(extra=None):
    batches = read_pending() + ([extra] if extra else [])
    results = []
    try:
        while batches:
            results.append(add_batch(batches[0]))
            batches.pop(0)
    except AnkiUnavailable as e:
        write_pending(batches)
        out({"anki": "closed", "queued_batches": len(batches), "added": results, "error": str(e),
             "hint": "Cards are queued; open Anki and run /expert:quiz flush."})
        return 1
    write_pending([])
    out({"added": results, "sync": try_sync() if results else "skipped"})
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    try:
        if cmd == "status":
            cmd_status()
        elif cmd == "add" and len(argv) > 2:
            with open(os.path.expanduser(argv[2]), encoding="utf-8") as f:
                batch = json.load(f)
            if not batch.get("deck") or not batch.get("cards"):
                raise ValueError("batch needs 'deck' and 'cards'")
            return flush(batch)
        elif cmd == "flush":
            return flush()
        else:
            print(__doc__)
            return 2
    except (RuntimeError, ValueError, OSError, KeyError) as e:
        out({"error": str(e)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
