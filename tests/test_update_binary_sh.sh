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

# Una version anterior queda como .prev (rollback manual o automatico).
check '[ -f "$new/version.txt" ] && [ -d "$new.prev" ]' "conserva la version anterior como .prev"

# glibc: un paquete compilado en un Ubuntu mas nuevo no se instala (no arrancaria).
pkgjson() {   # pkgjson NAME MINGLIBC
    pkg "$1" "$1"
    printf '{ "kind": "binary", "minGlibc": "%s" }\n' "$2" > "$work/pkg-$1/llamacode-install.json"
    tar -C "$work/pkg-$1" -czf "$work/$1.tar.gz" .
    ( cd "$work" && sha256sum "$1.tar.gz" > "$1.tar.gz.sha256" )
}
pkgjson newglibc 2.41
LC_GLIBC_VERSION=2.39 run --asset-url "$work/newglibc.tar.gz" --sha256-url "$work/newglibc.tar.gz.sha256" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q "needs glibc >= 2.41 and this system has 2.39" "$work/out.txt"' "glibc viejo: se niega y lo explica"
check '[ "$(cat "$inst/version.txt")" = envcheck ] && [ ! -e "$inst.new" ]' "glibc viejo: la instalacion queda intacta"
pkgjson okglibc 2.39
LC_GLIBC_VERSION=2.39 run --asset-url "$work/okglibc.tar.gz" --sha256-url "$work/okglibc.tar.gz.sha256" --install-dir "$inst" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ "$(cat "$inst/version.txt")" = okglibc ]' "glibc igual al minimo: instala"

# Standalone desde una shell con las variables del wrapper: launcher.env sale de ahi.
cfg2="$work/cfg2"
XDG_CONFIG_HOME="$cfg2" LLAMACODE_PROFILES_DIR="/media/x/it's here" LLAMACODE_LAUNCHER=/old/wrapper \
    run --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$work/opt/S1" && rc=0 || rc=$?
got="$(bash -c 'set -a; . "$1"; printf "%s|%s" "$LLAMACODE_PROFILES_DIR" "${LLAMACODE_LAUNCHER:-}"' _ "$cfg2/llamacode/launcher.env" 2>&1)"
check '[ $rc -eq 0 ] && [ "$got" = "/media/x/it'"'"'s here|" ]' "standalone: launcher.env con las LLAMACODE_* de la shell ($got)"

# Wrapper propio que define LLAMACODE_*: sin launcher.env no se toca el menu.
cfg3="$work/cfg3"; data3="$work/data3"
mkdir -p "$data3/applications" "$cfg3/autostart" "$work/bin3"
w3="$work/bin3/llamacode"
printf '#!/usr/bin/env bash\nexport LLAMACODE_PROFILES_DIR=/shared\nexec /x/LlamaCode "$@"\n' > "$w3"; chmod +x "$w3"
printf '[Desktop Entry]\nExec=%s %%U\n' "$w3" > "$data3/applications/llamacode.desktop"
printf '[Desktop Entry]\nExec=%s --startup\n' "$w3" > "$cfg3/autostart/llamacode.desktop"
XDG_CONFIG_HOME="$cfg3" XDG_DATA_HOME="$data3" run --asset-url "$work/v2.tar.gz" \
    --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$work/opt/S2" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -qF "Exec=$w3 %U" "$data3/applications/llamacode.desktop"' "wrapper sin launcher.env: la entrada del menu queda igual"
check 'grep -q "sets LLAMACODE_\* variables" "$work/out.txt" && grep -qF "Exec=$w3 --startup" "$cfg3/autostart/llamacode.desktop"' "wrapper sin launcher.env: avisa y no toca el autostart"
mkdir -p "$cfg3/llamacode"; echo "LLAMACODE_PROFILES_DIR=/shared" > "$cfg3/llamacode/launcher.env"
XDG_CONFIG_HOME="$cfg3" XDG_DATA_HOME="$data3" run --asset-url "$work/v2.tar.gz" \
    --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$work/opt/S2" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -qF "Exec=\"$work/opt/S2/llamacode\"" "$data3/applications/llamacode.desktop" && [ -f "$data3/applications/llamacode.desktop.bak" ]' "con launcher.env: el menu pasa al lanzador (.bak)"
check 'grep -qF "Exec=\"$work/opt/S2/llamacode\" --startup" "$cfg3/autostart/llamacode.desktop"' "con launcher.env: el autostart del wrapper se detecta solo"

# Rollback: si la version nueva muere con error al arrancar vuelve la anterior.
runl() { DISPLAY=:lc-test LC_HEALTH_SECONDS=2 bash "$src" "$@" --no-pause --no-shortcuts >"$work/out.txt" 2>&1; }
rb="$work/opt/RB"
run --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$rb" --no-shortcuts
pkg crash crash
printf '#!/bin/sh\necho "Could not load the Qt platform plugin" >&2\nexit 134\n' > "$work/pkg-crash/usr/bin/LlamaCode"
tar -C "$work/pkg-crash" -czf "$work/crash.tar.gz" .
( cd "$work" && sha256sum crash.tar.gz > crash.tar.gz.sha256 )
runl --asset-url "$work/crash.tar.gz" --sha256-url "$work/crash.tar.gz.sha256" --install-dir "$rb" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q "exited with code 134" "$work/out.txt" && grep -q "Qt platform plugin" "$work/out.txt"' "version nueva que crashea: lo informa con su salida"
check '[ "$(cat "$rb/version.txt")" = v2 ] && [ -x "$rb/llamacode" ] && [ "$(cat "$rb.failed/version.txt")" = crash ]' "vuelve la version anterior (la rota queda en .failed)"
pkg alive alive
printf '#!/bin/sh\nsleep 4\n' > "$work/pkg-alive/usr/bin/LlamaCode"
tar -C "$work/pkg-alive" -czf "$work/alive.tar.gz" .
( cd "$work" && sha256sum alive.tar.gz > alive.tar.gz.sha256 )
runl --asset-url "$work/alive.tar.gz" --sha256-url "$work/alive.tar.gz.sha256" --install-dir "$rb" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ "$(cat "$rb/version.txt")" = alive ]' "version nueva que sigue viva: queda instalada"
check '[ ! -e "$rb.failed" ]' "un update que anda borra la version rota (.failed) que habia quedado"
runl --asset-url "$work/v3.tar.gz" --sha256-url "$work/v3.tar.gz.sha256" --install-dir "$rb" && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ "$(cat "$rb/version.txt")" = v3 ]' "con la anterior abierta no queda el lock tomado; sale con 0 (le pasa el foco a otra instancia): no es rollback"

# Procedencia (attestation del CI) con un gh falso: nunca llama al gh real.
ghbin="$work/ghbin"; mkdir -p "$ghbin"
cat > "$ghbin/gh" <<'GH'
#!/bin/sh
case "$1 $2" in
    "auth status") exit "${FAKE_GH_AUTH:-0}" ;;
    "attestation verify")
        echo "$*" >> "$FAKE_GH_LOG"
        if [ -n "${FAKE_GH_FAIL:-}" ]; then echo "Error: HTTP 404: Not Found"; exit 1; fi
        echo "Verification succeeded"; exit 0 ;;
esac
exit 2
GH
chmod +x "$ghbin/gh"
export FAKE_GH_LOG="$work/gh.log"
att="$work/opt/ATT"
PATH="$ghbin:$PATH" run --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$att" --version 0.1.128 && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -q "Provenance verified" "$work/out.txt"' "release firmada: verifica la procedencia con gh"
check 'grep -q -- "--repo cristianlukas/UNLZ_Llamacode --signer-workflow cristianlukas/UNLZ_Llamacode/.github/workflows/release-binaries.yml" "$FAKE_GH_LOG"' "verifica contra el workflow de releases del repo"
PATH="$ghbin:$PATH" FAKE_GH_FAIL=1 run --asset-url "$work/v3.tar.gz" --sha256-url "$work/v3.tar.gz.sha256" --install-dir "$att" --version 0.1.130 && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q "Provenance check failed" "$work/out.txt" && grep -q "404" "$work/out.txt"' "sin attestation valida: no instala"
check '[ "$(cat "$att/version.txt")" = v2 ] && [ ! -e "$att.new" ]' "sin attestation valida: la instalacion queda intacta"
: > "$FAKE_GH_LOG"
PATH="$ghbin:$PATH" FAKE_GH_FAIL=1 run --asset-url "$work/v3.tar.gz" --sha256-url "$work/v3.tar.gz.sha256" --install-dir "$att" --version 0.1.127 && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ ! -s "$FAKE_GH_LOG" ]' "releases anteriores a la firma no se verifican"
PATH="$ghbin:$PATH" FAKE_GH_AUTH=1 run --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" --install-dir "$att" --version 0.1.128 && rc=0 || rc=$?
check '[ $rc -eq 0 ] && grep -q "Provenance not verified" "$work/out.txt" && [ ! -s "$FAKE_GH_LOG" ]' "sin gh logueado: avisa y sigue (el hash igual se verifica)"
PATH="$ghbin:$PATH" FAKE_GH_FAIL=1 LC_REQUIRE_ATTESTATION=1 run --asset-url "$work/v3.tar.gz" --sha256-url "$work/v3.tar.gz.sha256" --install-dir "$att" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q "Provenance check failed" "$work/out.txt"' "LC_REQUIRE_ATTESTATION exige la firma sin version"
PATH="$ghbin:$PATH" FAKE_GH_AUTH=1 LC_REQUIRE_ATTESTATION=1 run --asset-url "$work/v3.tar.gz" --sha256-url "$work/v3.tar.gz.sha256" --install-dir "$att" && rc=0 || rc=$?
check '[ $rc -eq 1 ] && grep -q "cannot be checked" "$work/out.txt" && [ "$(cat "$att/version.txt")" = v2 ]' "LC_REQUIRE_ATTESTATION sin gh logueado: no instala (no cae al hash solo)"

# La copia que el app deja en TMP se borra sola (con exito o con error).
mkdir -p "$work/tmp"
cp "$src" "$work/tmp/llamacode-update-binary-4242.sh"
bash "$work/tmp/llamacode-update-binary-4242.sh" --asset-url "$work/v2.tar.gz" --sha256-url "$work/v2.tar.gz.sha256" \
    --install-dir "$work/opt/T1" --no-launch --no-pause >"$work/out.txt" 2>&1 && rc=0 || rc=$?
check '[ $rc -eq 0 ] && [ ! -e "$work/tmp/llamacode-update-binary-4242.sh" ]' "el script copiado a TMP se borra al terminar"
cp "$src" "$work/tmp/llamacode-update-binary-4243.sh"
bash "$work/tmp/llamacode-update-binary-4243.sh" --asset-url "$work/v2.tar.gz" --install-dir "$work/opt/T1" \
    --no-launch --no-pause >"$work/out.txt" 2>&1 && rc=0 || rc=$?
check '[ $rc -eq 1 ] && [ ! -e "$work/tmp/llamacode-update-binary-4243.sh" ]' "tambien se borra si el update falla"
check '[ -f "$src" ]' "el script del repo (otro nombre) nunca se borra"

if [ $fails -eq 0 ]; then echo "TODO OK"; exit 0; fi
echo "$fails FALLAS"; exit 1
