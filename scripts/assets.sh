#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

export UV_PROJECT_ENVIRONMENT="$repo/.venv"
export UV_PYTHON_INSTALL_DIR="$repo/tools/python"
export UV_CACHE_DIR="$repo/.cache/uv"
export UV_TOOL_DIR="$repo/tools/uv-tools"

tools/uv/uv run python scripts/build_assets.py
