#!/usr/bin/env bash
set -euo pipefail

strata_root="${STRATA_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/strata-review-20261002/Strata-0.1.35}"
python_bin="${STRATA_PYTHON:-$strata_root/.venv/bin/python}"
config="${STRATA_CONFIG:-$strata_root/strata-iq3_s.json}"
port="${ASTRA_STRATA_PORT:-8350}"

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

exec "$python_bin" "$strata_root/serve/server.py" \
    --engine strata \
    --config "$config" \
    --port "$port"
