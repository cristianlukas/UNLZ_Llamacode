#!/usr/bin/env bash
# release.sh - publica un release Prod estable o Debug prerelease.
# Equivalente Linux de tools/release.ps1 (que necesita PowerShell).
#
# Uso:
#   scripts/release.sh                              # dry run Prod (version de CMakeLists.txt)
#   scripts/release.sh --channel debug --publish    # taggea HEAD y publica prerelease Debug
#   scripts/release.sh --bump --channel debug --publish
#                                                   # sube el patch, commitea, pushea y publica
#   scripts/release.sh --promote --publish          # publica como Prod el commit exacto
#                                                   # del ultimo vX.Y.Z-debug ya probado
#   scripts/release.sh --version 0.2.0 --publish
#
# Los tags son vX.Y.Z (Prod) y vX.Y.Z-debug (Debug): la app filtra por canal.
set -euo pipefail

channel="prod"
version=""
publish=0
bump=0
promote=0
force=0

usage() { sed -n '2,15p' "$0"; exit 2; }
fail() { echo "[ERROR] $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --channel) channel="${2:-}"; shift 2 ;;
        --version) version="${2:-}"; shift 2 ;;
        --publish) publish=1; shift ;;
        --bump) bump=1; shift ;;
        --promote) promote=1; shift ;;
        --force) force=1; shift ;;
        -h|--help) usage ;;
        *) echo "[ERROR] opcion desconocida: $1" >&2; usage ;;
    esac
done

channel="$(printf '%s' "$channel" | tr '[:upper:]' '[:lower:]')"
[ "$channel" = "prod" ] || [ "$channel" = "debug" ] || fail "canal invalido: $channel (prod|debug)"
[ $promote -eq 1 ] && channel="prod"
[ $promote -eq 1 ] && [ $bump -eq 1 ] && fail "--promote y --bump no se combinan: promote reusa la version del Debug"

root="$(git rev-parse --show-toplevel)"
cd "$root"

cmake_version() {
    sed -nE 's/^project\(LlamaCode VERSION ([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' CMakeLists.txt | head -1
}

target="HEAD"
if [ $promote -eq 1 ]; then
    src="$(git tag --list 'v*-debug' --sort=-v:refname | head -1)"
    [ -n "$src" ] || fail "no hay ningun tag vX.Y.Z-debug para promover"
    version="${src#v}"; version="${version%-debug}"
    target="$(git rev-list -n 1 "$src")"
elif [ -z "$version" ]; then
    version="$(cmake_version)"
    [ -n "$version" ] || fail "no pude leer la version de CMakeLists.txt"
    if [ $bump -eq 1 ]; then
        IFS=. read -r maj min pat <<<"$version"
        version="$maj.$min.$((pat + 1))"
    fi
fi
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "version invalida: '$version' (x.y.z)"

if [ "$channel" = "debug" ]; then
    tag="v$version-debug"; title="LlamaCode $version Debug"; pattern='^v[0-9]+\.[0-9]+\.[0-9]+-debug$'
else
    tag="v$version"; title="LlamaCode $version Prod"; pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
fi

prev="$(git tag --list 'v*' --sort=-v:refname | grep -E "$pattern" | grep -vx "$tag" | head -1 || true)"
range="$target"; [ -n "$prev" ] && range="$prev..$target"
notes="$(mktemp "${TMPDIR:-/tmp}/llamacode-release-XXXXXX.md")"
trap 'rm -f "$notes"' EXIT
git log --no-merges --pretty=format:'- %s' "$range" | head -40 > "$notes" || true
[ "$(git log --no-merges --oneline "$range" | wc -l)" -gt 40 ] && printf '\n- ...' >> "$notes"
[ -s "$notes" ] || echo "- Sin cambios registrados." > "$notes"

echo "== release $tag ($channel) =="
echo "  repo    : $root"
echo "  commit  : $(git rev-parse --short "$target")"
echo "  desde   : ${prev:-(primer release)}"
[ $bump -eq 1 ] && echo "  bump    : $(cmake_version) -> $version (commit + push antes del tag)"
[ $promote -eq 1 ] && echo "  promote : $src -> $tag (mismo commit)"
echo
sed 's/^/  /' "$notes"
echo

if [ $publish -eq 0 ]; then
    echo "[DRY RUN] Nada publicado. Repetir con --publish para taggear y publicar."
    exit 0
fi

command -v gh >/dev/null || fail "gh CLI no encontrado; instalalo o publica el release a mano."
if [ $force -eq 0 ]; then
    git diff --quiet && git diff --cached --quiet || fail "hay cambios sin commitear en archivos versionados (usa --force para ignorarlo)"
fi
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null && [ $force -eq 0 ]; then
    fail "el tag $tag ya existe; bumpear la version o usar --force"
fi

if [ $bump -eq 1 ]; then
    git fetch -q origin
    branch="$(git rev-parse --abbrev-ref HEAD)"
    if [ "$(git rev-list --count "HEAD..origin/$branch" 2>/dev/null || echo 0)" -gt 0 ]; then
        fail "origin/$branch tiene commits que no estan aca: integralos antes de bumpear"
    fi
    sed -i -E "s/^(project\(LlamaCode VERSION )[0-9]+\.[0-9]+\.[0-9]+/\1$version/" CMakeLists.txt
    [ "$(cmake_version)" = "$version" ] || fail "no pude escribir la version en CMakeLists.txt"
    label="$( [ "$channel" = debug ] && echo Debug || echo Prod )"
    git add CMakeLists.txt
    git commit -q -m "Release v$version ($label channel)"
    git push -q origin "HEAD:$branch"
    target="HEAD"
fi

if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
    git tag -a "$tag" "$target" -m "$title"
fi
git push -q origin "$tag"

args=(release create "$tag" --title "$title" --notes-file "$notes")
if [ "$channel" = "debug" ]; then args+=(--prerelease); else args+=(--latest); fi
gh "${args[@]}"
echo "[OK] Release $tag ($channel) publicado."
