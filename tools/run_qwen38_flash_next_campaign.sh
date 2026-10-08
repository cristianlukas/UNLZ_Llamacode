#!/usr/bin/env bash
set -euo pipefail

if ! command -v pwsh >/dev/null 2>&1; then
  echo "pwsh is required to run the cross-platform Flash-Next campaign" >&2
  exit 127
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec pwsh -NoProfile -File "$script_dir/run_qwen38_flash_next_campaign.ps1" "$@"
