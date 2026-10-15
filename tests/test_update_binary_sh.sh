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
check 'grep -q "Exec=\"$inst/llamacode\"" "$XDG_DATA_HOME/applications/llamacode.desktop"' "crea la entrada del menu (via el lanzador)"

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
check '[ -f "$XDG_DATA_HOME/applications/llamacode-debug.desktop" ]' "Debug tiene su propia entrada de menu"

check 'grep -q "Exec=\"$dbg/llamacode\" --startup" "$XDG_CONFIG_HOME/autostart/llamacode.desktop"' "el autostart pasa por el lanzador"

# Lanzador: limpia el Qt de un wrapper de desarrollo y lee launcher.env.
pkg envcheck envcheck
printf '#!/bin/sh\nprintf "%%s|%%s|%%s|%%s" "$LLAMACODE_PROFILES_DIR" "$LD_LIBRARY_PATH" "$LLAMACODE_LAUNCHER" "$PWD"\n' \
    > "$work/pkg-envcheck/usr/bin/LlamaCode"
tar -C "$work/pkg-envcheck" -czf "$work/envcheck.tar.gz" .
( cd "$work" && sha256sum envcheck.tar.gz > envcheck.tar.gz.sha256 )
mkdir -p "$XDG_CONFIG_HOME/llamacode"
printf "LLAMACODE_PROFILES_DIR='/media/x/Llama Code/profiles'\n" > "$XDG_CONFIG_HOME/llamacode/launcher.env"
run --asset-url "$work/envcheck.tar.gz" --sha256-url "$work/envcheck.tar.gz.sha256" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ -x "$inst/llamacode" ]' "escribe el lanzador ejecutable"
out="$(LD_LIBRARY_PATH=/home/u/Qt/lib "$inst/llamacode")"
check '[ "$out" = "/media/x/Llama Code/profiles||$inst/llamacode|$inst/usr/bin" ]' "el lanzador lee launcher.env y limpia LD_LIBRARY_PATH ($out)"
check 'grep -q "Exec=\"$inst/llamacode\"" "$XDG_DATA_HOME/applications/llamacode.desktop"' "la entrada del menu usa el lanzador"

# Migracion desde un wrapper propio: mismo id de .desktop que el que crea el
# script. Se guarda una copia y el autostart del wrapper pasa al lanzador; el
# de llamacode-debug (prefijo comun) no se toca.
apps="$XDG_DATA_HOME/applications"
wrap="$HOME/.local/bin/llamacode"
printf '[Desktop Entry]\nExec=%s %%U\n' "$wrap" > "$apps/llamacode.desktop"
printf '[Desktop Entry]\nExec=%s-debug %%U\n' "$wrap" > "$apps/llamacode-debug.desktop"
printf '[Desktop Entry]\nExec="%s" --startup\n' "$wrap" > "$XDG_CONFIG_HOME/autostart/llamacode.desktop"
new="$work/opt/LlamaCode-New"
run --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$new" --legacy-launcher "$wrap" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -qF "$wrap %U" "$apps/llamacode.desktop.bak"' "guarda la entrada del menu del wrapper como .bak"
check 'grep -q "Exec=\"$new/llamacode\" --startup" "$XDG_CONFIG_HOME/autostart/llamacode.desktop"' "el autostart del wrapper pasa al lanzador"
check 'grep -qF "Exec=$wrap-debug %U" "$apps/llamacode-debug.desktop"' "no toca la entrada de llamacode-debug (prefijo comun)"

# Herramientas que el paquete no puede traer: avisa, no frena.
LC_RUNTIME_TOOLS="bash lc-tool-que-no-existe" run --asset-url "$work/v2.tar.gz" \
    --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$new" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -q "Missing optional tools: lc-tool-que-no-existe.\[0m$" "$work/out.txt"' "avisa las herramientas faltantes sin fallar"
LC_RUNTIME_TOOLS="bash" run --asset-url "$work/v2.tar.gz" \
    --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$new" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && ! grep -q "Missing optional" "$work/out.txt"' "sin faltantes no avisa"

# tesseract sin el idioma espanol: avisa el paquete del idioma (tesseract falso).
mkdir -p "$work/fakebin"
printf '#!/bin/sh\necho "List of available languages (2):"\necho eng\necho osd\n' > "$work/fakebin/tesseract"
chmod +x "$work/fakebin/tesseract"
PATH="$work/fakebin:$PATH" LC_RUNTIME_TOOLS="tesseract" run --asset-url "$work/v2.tar.gz" \
    --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$new" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -q "Missing optional tools: tesseract-ocr-spa" "$work/out.txt"' "tesseract sin espanol: avisa tesseract-ocr-spa"

if [ $fails -eq 0 ]; then echo "TODO OK"; exit 0; fi
echo "$fails FALLAS"; exit 1
