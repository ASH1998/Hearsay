#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

export UV_PROJECT_ENVIRONMENT="$repo/.venv"
export UV_PYTHON_INSTALL_DIR="$repo/tools/python"
export UV_CACHE_DIR="$repo/.cache/uv"
export UV_TOOL_DIR="$repo/tools/uv-tools"
export HF_HOME="$repo/.cache/huggingface"
export TORCH_HOME="$repo/.cache/torch"
export PLAYWRIGHT_BROWSERS_PATH="$repo/.cache/ms-playwright"
export COREPACK_HOME="$repo/.cache/corepack"
export CI=true

uv_dir="$repo/tools/uv"
uv_bin="$uv_dir/uv"
if [ ! -x "$uv_bin" ]; then
  mkdir -p "$uv_dir"
  export UV_UNMANAGED_INSTALL="$uv_dir"
  curl -LsSf "https://releases.astral.sh/github/uv/releases/download/0.11.15/uv-installer.sh" | sh
fi

"$uv_bin" --version | grep "uv 0.11.15"
"$uv_bin" python install 3.12
python_bin="$repo/tools/python/cpython-3.12.13-linux-x86_64-gnu/bin/python3"
"$uv_bin" sync --all-groups --python "$python_bin"
corepack pnpm@11.9.0 install --frozen-lockfile
corepack pnpm@11.9.0 exec playwright install chromium

printf '%s\n' "Bootstrap complete. Run 'corepack pnpm@11.9.0 doctor', then 'corepack pnpm@11.9.0 dev'."
