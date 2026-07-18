#!/usr/bin/env sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo"

test -f assets/manifest.json
printf '%s\n' "Asset manifest exists. Run the PowerShell validator for byte-budget checks."
