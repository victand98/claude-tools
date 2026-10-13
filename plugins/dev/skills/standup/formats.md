# Standup formats

Map the item list to the chosen format. To add a format, copy a block and give it a new name.

## classic (default)
```
**Yesterday:** max 3 short sentences.
**Today:** max 2 short sentences.
**Blockers:** "None right now" or the blocker.
**Pronunciation:** at most 2 hard words, e.g. "column (KOL-um)". Skip if none.
```

## done-next
```
Done
- one short line per finished item (max 4)
Next
- one short line per next item (max 3)
```
Blockers go as a `Next` line starting with "Waiting on" or "Blocked by". No pronunciation line.

## done-next-blockers
```
Done
- (max 4)
Next
- (max 3)
Blockers
- "None" or one line per blocker
```

## slack
One line, ready to paste:
```
✅ Done: ... · 🔜 Next: ... · 🚧 Blockers: none
```
