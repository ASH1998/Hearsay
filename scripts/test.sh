#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

export UV_PROJECT_ENVIRONMENT="$repo/.venv"
export UV_PYTHON_INSTALL_DIR="$repo/tools/python"
export UV_CACHE_DIR="$repo/.cache/uv"
export UV_TOOL_DIR="$repo/tools/uv-tools"
export CI=true

tools/uv/uv run ruff check apps/api/src apps/api/tests scripts
tools/uv/uv run ruff format --check apps/api/src apps/api/tests scripts
tools/uv/uv run mypy apps/api/src
tools/uv/uv run pytest
tools/uv/uv run python scripts/run_database_tests.py
tools/uv/uv run python scripts/build_assets.py --validate-only
pnpm --filter @hearsay/web lint
pnpm --filter @hearsay/web typecheck
pnpm --filter @hearsay/web test
pnpm test:e2e
