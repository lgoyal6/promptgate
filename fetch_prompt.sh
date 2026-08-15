#!/usr/bin/env bash
# Fetches Parahelp's published manager prompt. Not redistributed in this repo.
set -euo pipefail
URL="https://raw.githubusercontent.com/dontriskit/awesome-ai-system-prompts/main/Parahelp/manager.md"
curl -sSLo manager.md "$URL"
printf 'manager.md: %s bytes, %s lines\n' "$(wc -c < manager.md | tr -d ' ')" "$(wc -l < manager.md | tr -d ' ')"
