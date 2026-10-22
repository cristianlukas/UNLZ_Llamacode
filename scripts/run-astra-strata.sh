#!/usr/bin/env bash
set -euo pipefail

strata_root="${STRATA_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/strata-review-20261002/Strata-0.1.35}"
python_bin="${STRATA_PYTHON:-$strata_root/.venv/bin/python}"
config="${STRATA_CONFIG:-$strata_root/strata-iq3_s.json}"
port="${ASTRA_STRATA_PORT:-8350}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname -- "$script_dir")"
scope_python="${STRATA_SCOPE_PYTHON:-python3}"
scope_cli="$repo_root/tools/linux_eval_scope.py"

if [[ ! -x "$python_bin" ]]; then
    printf 'No encuentro el Python de Strata: %s\n' "$python_bin" >&2
    exit 1
fi
if [[ ! -f "$strata_root/serve/server.py" ]]; then
    printf 'No encuentro el servidor Strata en: %s\n' "$strata_root/serve/server.py" >&2
    exit 1
fi
if [[ ! -f "$config" ]]; then
    printf 'No encuentro la configuración ASTRA IQ3_S: %s\n' "$config" >&2
    exit 1
fi
if [[ ! -f "$scope_cli" ]]; then
    printf 'No encuentro el launcher protegido de evaluaciones: %s\n' "$scope_cli" >&2
    exit 1
fi

exec "$scope_python" "$scope_cli" --run -- "$python_bin" "$strata_root/serve/server.py" \
    --engine strata \
    --config "$config" \
    --port "$port"
