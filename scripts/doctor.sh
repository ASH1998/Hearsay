#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

node --version
corepack pnpm@11.9.0 --version
tools/uv/uv --version
tools/uv/uv run python --version
test -f .env.example
test -f apps/web/public/sprites/player/newcomer-idle-south.png
tools/uv/uv run python scripts/check_database.py
tools/uv/uv run python scripts/check_embeddings.py
tools/uv/uv run python scripts/check_inference.py

printf '%s\n' "Doctor passed."
