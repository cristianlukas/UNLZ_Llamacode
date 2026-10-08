#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/cristianlukas/UNLZ_Llamacode.git"
DIR="${LC_DIR:-$HOME/LlamaCode}"
REF="${LC_REF:-}"
BRANCH="${LC_BRANCH:-main}"
CONFIG="${LC_CONFIG:-Release}"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
info() { printf '[*] %s\n' "$*"; }

[[ "$CONFIG" == Debug || "$CONFIG" == Release ]] || fail "LC_CONFIG must be Debug or Release."
if [[ -n "$REF" && ! "$REF" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-debug)?$ ]]; then
    fail "Invalid release ref: $REF"
fi
[[ -d "$DIR/.git" ]] || fail "No Git checkout at $DIR. Install LlamaCode first, then retry."

dirty="$(git -C "$DIR" status --porcelain)"
[[ -z "$dirty" ]] || fail "Checkout has local changes; refusing to overwrite them. Commit or stash them first."

if [[ -n "$REF" ]]; then
    info "Fetching release $REF"
    git -C "$DIR" fetch --depth 1 origin "refs/tags/$REF:refs/tags/$REF"
    git -C "$DIR" checkout --detach "$REF"
    git -C "$DIR" reset --hard "$REF"
else
    info "Fetching branch $BRANCH"
    git -C "$DIR" fetch --depth 1 origin "$BRANCH"
    git -C "$DIR" checkout "$BRANCH"
    git -C "$DIR" reset --hard "origin/$BRANCH"
fi

info "Building $CONFIG from ${REF:-$BRANCH}"
LC_BUILD_DIR="${LC_BUILD_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/llamacode/build_linux}" \
    "$DIR/scripts/build-linux.sh" "$CONFIG"

BUILD_DIR="${LC_BUILD_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/llamacode/build_linux}"
EXE="$BUILD_DIR/LlamaCode"
[[ -x "$EXE" ]] || fail "Built executable missing: $EXE"

QTROOT="${LC_QTROOT:-$HOME/Qt}"
QTDIR="${LC_QTDIR:-$QTROOT/${LC_QTVER:-6.8.3}/gcc_64}"
info "Launching updated LlamaCode"
(
    cd "$BUILD_DIR"
    LD_LIBRARY_PATH="$QTDIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$EXE" >/dev/null 2>&1 &
)
