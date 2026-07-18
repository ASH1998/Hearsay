#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

node --version
pnpm --version
tools/uv/uv --version
tools/uv/uv run python --version
docker --version
test -f .env.example
test -f assets/manifest.json

printf '%s\n' "Doctor passed."
