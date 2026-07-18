#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

export UV_PROJECT_ENVIRONMENT="$repo/.venv"
export UV_PYTHON_INSTALL_DIR="$repo/tools/python"
export UV_CACHE_DIR="$repo/.cache/uv"
export UV_TOOL_DIR="$repo/tools/uv-tools"

tools/uv/uv run uvicorn hearsay_api.main:app --app-dir apps/api/src --reload --port 8000 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
pnpm --filter @hearsay/web dev
