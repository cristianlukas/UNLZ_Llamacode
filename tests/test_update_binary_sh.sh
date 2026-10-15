#!/usr/bin/env bash
# Test de scripts/update-binary.sh ("Actualizar" con binario en Linux) contra
# tarballs falsos locales: nunca baja nada ni toca la instalacion real.
set -euo pipefail

src="$(cd "$(dirname "$0")/.." && pwd)/scripts/update-binary.sh"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
export HOME="$work/home" XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config"
mkdir -p "$HOME"
unset DISPLAY WAYLAND_DISPLAY
fails=0
check() { if eval "$1"; then echo "  PASS $2"; else echo "  FAIL $2"; fails=$((fails + 1)); fi; }

pkg() {   # pkg NAME CONTENT [nobin] -> $work/NAME.tar.gz (+ .sha256)
    local d="$work/pkg-$1"
    mkdir -p "$d/usr/bin"
    if [ -z "${3:-}" ]; then printf '#!/bin/sh\necho %s\n' "$2" > "$d/usr/bin/LlamaCode"; chmod +x "$d/usr/bin/LlamaCode"; fi
    echo "$2" > "$d/version.txt"
    tar -C "$d" -czf "$work/$1.tar.gz" .
    ( cd "$work" && sha256sum "$1.tar.gz" > "$1.tar.gz.sha256" )
}
run() { bash "$src" "$@" --no-launch --no-pause >"$work/out.txt" 2>&1; }

echo "== update-binary.sh =="
inst="$work/opt/LlamaCode"
mkdir -p "$inst"; echo v1 > "$inst/version.txt"; echo x > "$inst/stale.so"

pkg v2 v2
run --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 0 ]' "instala con hash verificado (rc=$rc)"
check '[ "$(cat "$inst/version.txt")" = v2 ]' "la carpeta queda con la version nueva"
check '[ ! -e "$inst/stale.so" ]' "no quedan archivos viejos (swap de carpeta)"
check '[ ! -e "$inst.old" ] && [ ! -e "$inst.new" ]' "no deja .old ni .new"
check 'grep -q "Exec=\"$inst/usr/bin/LlamaCode\"" "$XDG_DATA_HOME/applications/llamacode.desktop"' "crea la entrada del menu"

pkg v3 v3
run --asset-url "file://$work/v3.tar.gz" --sha256 "$(printf '0%.0s' $(seq 64))" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q "SHA-256 mismatch" "$work/out.txt"' "hash equivocado: sale 1 y lo explica"
check '[ "$(cat "$inst/version.txt")" = v2 ]' "con hash equivocado la instalacion queda intacta"

run --asset-url "$work/v3.tar.gz" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q unverified "$work/out.txt"' "sin SHA-256 no instala"

pkg broken broken nobin
run --asset-url "$work/broken.tar.gz" --sha256-url "$work/broken.tar.gz.sha256" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && [ "$(cat "$inst/version.txt")" = v2 ]' "paquete sin usr/bin/LlamaCode: no reemplaza"

# Migracion desde un checkout: el autostart que lanzaba el binario viejo pasa al nuevo.
mkdir -p "$XDG_CONFIG_HOME/autostart"
legacy="$HOME/LlamaCode/build/LlamaCode"
printf '[Desktop Entry]\nExec="%s" --startup\n' "$legacy" > "$XDG_CONFIG_HOME/autostart/llamacode.desktop"
dbg="$work/opt/LlamaCode-Debug"
run --asset-url "$work/v3.tar.gz" --sha256 "$(cut -d' ' -f1 "$work/v3.tar.gz.sha256" | tr a-f A-F)" \
    --install-dir "$dbg" --channel debug --legacy-exe "$legacy" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ -x "$dbg/usr/bin/LlamaCode" ]' "instala en carpeta nueva (migracion), hash en mayuscula"
check 'grep -q "Exec=\"$dbg/usr/bin/LlamaCode\" --startup" "$XDG_CONFIG_HOME/autostart/llamacode.desktop"' "el autostart apunta a la instalacion nueva"
check '[ -f "$XDG_DATA_HOME/applications/llamacode-debug.desktop" ]' "Debug tiene su propia entrada de menu"

if [ $fails -eq 0 ]; then echo "TODO OK"; exit 0; fi
echo "$fails FALLAS"; exit 1
