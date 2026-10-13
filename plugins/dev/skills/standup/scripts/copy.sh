#!/usr/bin/env bash
# Copies a saved standup file to the clipboard.
# Usage: copy.sh <file>
set -u
file="${1:-}"
[ -f "$file" ] || { echo "File not found: $file"; exit 0; }

if command -v pbcopy >/dev/null 2>&1; then pbcopy < "$file"
elif command -v wl-copy >/dev/null 2>&1; then wl-copy < "$file"
elif command -v xclip >/dev/null 2>&1; then xclip -selection clipboard < "$file"
elif command -v clip.exe >/dev/null 2>&1; then clip.exe < "$file"
else echo "No clipboard tool found (pbcopy, wl-copy, xclip, clip.exe)"; exit 0
fi
echo "Copied to clipboard."
