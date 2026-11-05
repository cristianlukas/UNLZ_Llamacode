#!/usr/bin/env bash
# Instala agent-desktop (github.com/vercel-labs/agent-desktop) donde LlamaCode lo
# busca: ~/.local/share/LlamaCode/LlamaCode/tools/agent-desktop/agent-desktop.
# Con el binario presente, desktop_controls / desktop_click_element /
# desktop_control_action en Linux pasan por agent-desktop y AT-SPI queda de
# fallback (docs/charla-multitarea-computer-use-20261105.md).
#
# Uso: scripts/install-agent-desktop.sh [--version v1.2.0] [--dest DIR]
set -euo pipefail

VERSION="v1.2.0"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/LlamaCode/LlamaCode/tools/agent-desktop"
while [ $# -gt 0 ]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --dest) DEST="$2"; shift 2 ;;
        -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
        *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
    esac
done

case "$(uname -m)" in
    x86_64) ARCH=x86_64 ;;
    aarch64|arm64) ARCH=aarch64 ;;
    *) echo "Arquitectura no soportada: $(uname -m)" >&2; exit 2 ;;
esac
ASSET="agent-desktop-${VERSION}-${ARCH}-unknown-linux-gnu.tar.gz"
BASE="https://github.com/vercel-labs/agent-desktop/releases/download/${VERSION}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL -o "$TMP/$ASSET" "$BASE/$ASSET"
curl -fsSL -o "$TMP/checksums.txt" "$BASE/checksums.txt"
(cd "$TMP" && grep " ${ASSET}\$" checksums.txt | sha256sum -c -) \
    || { echo "SHA-256 no coincide: no se instala." >&2; exit 1; }

mkdir -p "$TMP/x"
tar -xzf "$TMP/$ASSET" -C "$TMP/x"
[ -x "$TMP/x/agent-desktop" ] || { echo "El paquete no trae agent-desktop." >&2; exit 1; }
mkdir -p "$DEST"
install -m 0755 "$TMP/x/agent-desktop" "$DEST/agent-desktop"
[ -f "$TMP/x/agent-desktop-linux-clipboard-owner" ] \
    && install -m 0755 "$TMP/x/agent-desktop-linux-clipboard-owner" "$DEST/"
"$DEST/agent-desktop" version
echo "Instalado en $DEST. Para que AT-SPI vea las apps: at-spi2-core activo en la sesión."
