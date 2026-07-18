#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

node --version
pnpm --version
tools/uv/uv --version
tools/uv/uv run python --version
test -f .env.example
test -f assets/manifest.json
tools/uv/uv run python scripts/build_assets.py --validate-only
tools/uv/uv run python scripts/check_database.py
tools/uv/uv run python scripts/check_inference.py

printf '%s\n' "Doctor passed."
