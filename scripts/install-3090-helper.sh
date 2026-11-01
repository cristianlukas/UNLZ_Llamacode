#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"
if [[ ${EUID:-$(id -u)} -ne 0 ]] && ! sudo -n -v >/dev/null 2>&1; then
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec "$ROOT_DIR/scripts/install-3090-helper.sh"
    fi
    echo 'Se necesita sudo o pkexec para instalar el servicio de verificación de arranque.' >&2
    exit 77
fi

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    TARGET_UID="${PKEXEC_UID:-${SUDO_UID:-}}"
    if [[ -z "$TARGET_UID" ]]; then
        echo 'No se pudo identificar al usuario de la sesión gráfica (PKEXEC_UID ausente).' >&2
        exit 77
    fi
    TARGET_ENTRY="$(getent passwd "$TARGET_UID")"
    TARGET_USER="$(cut -d: -f1 <<< "$TARGET_ENTRY")"
    TARGET_HOME="$(cut -d: -f6 <<< "$TARGET_ENTRY")"
    TARGET_GID="$(id -g "$TARGET_USER")"
else
    TARGET_UID="$(id -u)"
    TARGET_USER="$(id -un)"
    TARGET_HOME="$HOME"
    TARGET_GID="$(id -g)"
fi

BUILD_DIR="${LC_BUILD_DIR:-${XDG_CACHE_HOME:-$TARGET_HOME/.cache}/llamacode/build_linux}"
BIN="${BUILD_DIR}/3090-helper"

privileged_install() {
    if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

if [[ ! -x "$BIN" ]]; then
    echo "No encuentro $BIN. Compilá primero el target lc_3090_helper." >&2
    exit 2
fi

privileged_install install -D -o root -g root -m 0755 "$BIN" "$PREFIX/bin/3090-helper"
privileged_install install -D -o root -g root -m 0755 \
    "$ROOT_DIR/scripts/3090-helper-admin" "$PREFIX/libexec/3090-helper-admin"
UNIT_TMP="$(mktemp)"
POLICY_TMP="$(mktemp)"
trap 'rm -f "$UNIT_TMP" "$POLICY_TMP"' EXIT
sed "s|@PREFIX@|$PREFIX|g" \
    "$ROOT_DIR/packaging/linux/3090-helper-verify-boot.service" > "$UNIT_TMP"
sed "s|@LC_3090_HELPER_ADMIN_PATH@|$PREFIX/libexec/3090-helper-admin|g" \
    "$ROOT_DIR/packaging/linux/org.llamacode.3090-helper.policy.in" > "$POLICY_TMP"
privileged_install install -D -o root -g root -m 0644 \
    "$UNIT_TMP" /etc/systemd/system/3090-helper-verify-boot.service
privileged_install install -D -o root -g root -m 0644 \
    "$POLICY_TMP" /usr/share/polkit-1/actions/org.llamacode.3090-helper.policy
privileged_install systemctl daemon-reload
privileged_install systemctl enable 3090-helper-verify-boot.service
if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    install -d -o "$TARGET_UID" -g "$TARGET_GID" -m 0755 "$TARGET_HOME/.config/autostart"
else
    mkdir -p "$TARGET_HOME/.config/autostart"
fi
sed "s|/usr/local/bin/3090-helper|$PREFIX/bin/3090-helper|" \
    "$ROOT_DIR/packaging/linux/3090-helper.desktop" \
    > "$TARGET_HOME/.config/autostart/3090-helper.desktop.tmp"
if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    install -o "$TARGET_UID" -g "$TARGET_GID" -m 0644 \
        "$TARGET_HOME/.config/autostart/3090-helper.desktop.tmp" \
        "$TARGET_HOME/.config/autostart/3090-helper.desktop"
    rm -f "$TARGET_HOME/.config/autostart/3090-helper.desktop.tmp"
else
    mv "$TARGET_HOME/.config/autostart/3090-helper.desktop.tmp" \
       "$TARGET_HOME/.config/autostart/3090-helper.desktop"
    chmod 0644 "$TARGET_HOME/.config/autostart/3090-helper.desktop"
fi
echo '3090 HELPER instalado; se inicia al próximo login gráfico como usuario de la sesión.'
echo 'La verificación de arranque quedó habilitada para el próximo inicio de Ubuntu.'
