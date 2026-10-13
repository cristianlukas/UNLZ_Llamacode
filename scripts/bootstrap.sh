#!/usr/bin/env bash
# LlamaCode zero-to-running bootstrap for Linux.
#
# Installs build/runtime and Linux desktop dependencies (git, rsync, cmake,
# ninja, g++, Python, Qt 6.8.3 via aqtinstall, X11 tools, AT-SPI2, Tesseract
# and bubblewrap), clones the repo into an isolated folder, builds and launches.
#
#   curl -fsSL https://raw.githubusercontent.com/cristianlukas/UNLZ_Llamacode/main/scripts/bootstrap.sh | bash
#
# Qt is installed via aqtinstall (not distro packages) because the code needs
# Qt >= 6.5 (QQmlApplicationEngine::loadFromModule) and most LTS distros ship an
# older Qt (e.g. Ubuntu 24.04 = 6.4.2). aqt guarantees a consistent 6.8.3.
#
# Override defaults via env vars:
#   LC_DIR=/path/to/install   (default: $HOME/LlamaCode)
#   LC_BRANCH=main
#   LC_CONFIG=Release         (Release default = canal Prod estable; Debug = prerelease)
#   LC_QTVER=6.8.3
#   LC_QTROOT=$HOME/Qt
#   LC_NORUN=1                (skip launching)

set -euo pipefail

REPO="https://github.com/cristianlukas/UNLZ_Llamacode.git"
DIR="${LC_DIR:-$HOME/LlamaCode}"
BRANCH="${LC_BRANCH:-main}"
CONFIG="${LC_CONFIG:-Release}"
[[ "$CONFIG" == Debug || "$CONFIG" == Release ]] || c_die "LC_CONFIG must be Debug or Release."
QTVER="${LC_QTVER:-6.8.3}"
QTROOT="${LC_QTROOT:-$HOME/Qt}"

c_info() { printf '\033[36m[*] %s\033[0m\n' "$*"; }
c_ok()   { printf '\033[32m[OK] %s\033[0m\n' "$*"; }
c_die()  { printf '\033[31m[ERROR] %s\033[0m\n' "$*" >&2; exit 1; }

echo ""
printf '\033[35m=== LlamaCode bootstrap (Linux) ===\033[0m\n'
echo "Target: $DIR  branch=$BRANCH  config=$CONFIG  Qt=$QTVER"
echo ""

# ── Privilege escalation helper ──────────────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else
        c_die "Need root or sudo to install system packages."
    fi
fi

# ── Toolchain, Qt runtime/link and Linux desktop libraries (distro packages) ─
# We install the C++ toolchain, system libraries that the aqt-built Qt links
# against, and dependencies for Linux desktop automation/sandboxing -- NOT
# distro Qt itself.
# libpulse: libQt6Multimedia.so (aqt) tiene NEEDED libpulse.so.0; sin ella el
# link de LlamaCode falla con "undefined reference to pa_*@PULSE_0".
# libsecret (-dev) builds QtKeychain's Secret Service backend for storing cloud
# API keys in the OS keyring. Without it that build fails; with
# -DLC_USE_QTKEYCHAIN=OFF, or without an available keyring at runtime, the file
# fallback is used and is not encrypted (it is restricted to the current user).
install_deps() {
    if command -v apt-get >/dev/null 2>&1; then
        c_info "Installing toolchain + Qt runtime libs via apt..."
        $SUDO apt-get update -y
        $SUDO apt-get install -y --no-install-recommends \
            git curl ca-certificates rsync cmake ninja-build build-essential pkg-config \
            python3 python3-pip python3-venv \
            libglib2.0-0 libgl1-mesa-dev libegl1 libxkbcommon0 libxkbcommon-x11-0 \
            libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
            libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
            libfontconfig1 libfreetype6 libdbus-1-3 libpulse0 \
            libsecret-1-dev \
            x11-utils xdotool wmctrl at-spi2-core tesseract-ocr tesseract-ocr-spa \
            bubblewrap
    elif command -v dnf >/dev/null 2>&1; then
        c_info "Installing toolchain + Qt runtime libs via dnf..."
        $SUDO dnf install -y \
            git curl rsync cmake ninja-build gcc-c++ make pkgconf-pkg-config \
            python3 python3-pip \
            glib2 mesa-libGL-devel mesa-libEGL libxkbcommon libxkbcommon-x11 \
            xcb-util-cursor fontconfig freetype dbus-libs pulseaudio-libs libsecret-devel \
            xorg-x11-utils xdotool wmctrl at-spi2-core tesseract bubblewrap
    elif command -v pacman >/dev/null 2>&1; then
        c_info "Installing toolchain + Qt runtime libs via pacman..."
        $SUDO pacman -Sy --needed --noconfirm \
            git curl rsync cmake ninja base-devel python python-pip \
            glib2 mesa libxkbcommon libxkbcommon-x11 xcb-util-cursor fontconfig freetype2 dbus libpulse libsecret \
            xorg-xprop xorg-xwininfo xdotool wmctrl at-spi2-core tesseract tesseract-data-spa bubblewrap
    elif command -v zypper >/dev/null 2>&1; then
        c_info "Installing toolchain + Qt runtime libs via zypper..."
        $SUDO zypper install -y \
            git curl rsync cmake ninja gcc-c++ pkg-config python3 python3-pip \
            libglib-2_0-0 Mesa-libGL-devel libxkbcommon0 libxkbcommon-x11-0 \
            xcb-util-cursor0 fontconfig freetype2 libdbus-1-3 libpulse0 libsecret-devel \
            xorg-x11 xdotool wmctrl at-spi2-core tesseract-ocr bubblewrap
    else
        c_die "Unsupported distro: install git, cmake, ninja, g++, python3 and Qt6 runtime libs manually."
    fi
}
install_deps

command -v cmake  >/dev/null 2>&1 || c_die "cmake not found after install."
command -v git    >/dev/null 2>&1 || c_die "git not found after install."
command -v ninja  >/dev/null 2>&1 || c_die "ninja not found after install."
c_ok "toolchain"

# ── Qt 6.8.3 via aqtinstall ──────────────────────────────────────────────────
# Multimedia es add-on en aqt (Svg ya viene en la base): sin pedirlo, el
# find_package(Qt6 ... Multimedia) de CMakeLists.txt falla en una maquina limpia.
QTDIR="$QTROOT/$QTVER/gcc_64"
QT_AQT_MODULES=(qtmultimedia)
QT_REQUIRED_COMPONENTS=(Core Quick QuickControls2 Sql Concurrent Network Widgets Multimedia Svg)
missing_qt_components() {
    local c
    for c in "${QT_REQUIRED_COMPONENTS[@]}"; do
        [ -f "$QTDIR/lib/cmake/Qt6$c/Qt6${c}Config.cmake" ] || printf '%s ' "$c"
    done
}
install_qt() {
    c_info "Installing Qt $QTVER (linux gcc_64) via aqtinstall..."
    # Isolated venv so we never fight system pip / PEP 668.
    if [ ! -x "$HOME/.lc-aqt-venv/bin/aqt" ]; then
        python3 -m venv "$HOME/.lc-aqt-venv" || c_die "python3 -m venv failed (install python3-venv)."
        "$HOME/.lc-aqt-venv/bin/pip" install --upgrade pip >/dev/null
        "$HOME/.lc-aqt-venv/bin/pip" install aqtinstall >/dev/null || c_die "pip install aqtinstall failed."
    fi
    "$HOME/.lc-aqt-venv/bin/aqt" install-qt linux desktop "$QTVER" linux_gcc_64         -O "$QTROOT" --modules "${QT_AQT_MODULES[@]}"         || c_die "aqt install-qt failed. Check your connection and re-run."
}
if [ ! -f "$QTDIR/lib/cmake/Qt6/Qt6Config.cmake" ]; then
    install_qt
elif [ -n "$(missing_qt_components)" ]; then
    c_info "Qt exists but is missing: $(missing_qt_components)-- installing add-on modules..."
    install_qt
fi
[ -f "$QTDIR/lib/cmake/Qt6/Qt6Config.cmake" ] || c_die "Qt6 not found at $QTDIR after install."
[ -z "$(missing_qt_components)" ] || c_die "Qt6 at $QTDIR is incomplete. Missing: $(missing_qt_components)"
c_ok "Qt6: $QTDIR"

# ── Clone / update ───────────────────────────────────────────────────────────
if [ -d "$DIR/.git" ]; then
    c_info "Repo exists -- pulling latest..."
    if [ -n "$(git -C "$DIR" status --porcelain)" ]; then
        c_die "Repo existente con cambios sin commitear: no se hace reset destructivo. Usá otro LC_DIR o limpiá el tree conscientemente."
    fi
    git -C "$DIR" fetch --depth 1 origin "$BRANCH"
    git -C "$DIR" checkout "$BRANCH"
    git -C "$DIR" reset --hard "origin/$BRANCH"
else
    c_info "Cloning into $DIR ..."
    git clone --depth 1 --branch "$BRANCH" "$REPO" "$DIR"
fi
c_ok "source ready"

# ── Build ────────────────────────────────────────────────────────────────────
BUILD_DIR="$DIR/build"
c_info "Configuring..."
cmake -S "$DIR" -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE="$CONFIG" \
    -DCMAKE_PREFIX_PATH="$QTDIR"

c_info "Building..."
cmake --build "$BUILD_DIR" -j "$(nproc)"

EXE="$BUILD_DIR/LlamaCode"
[ -x "$EXE" ] || c_die "Built binary not found at $EXE"

echo ""
c_ok "Done. Binary: $EXE"
echo ""

if [ -z "${LC_NORUN:-}" ]; then
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        # Desacoplada de la terminal: con '( ... & )' heredaba stdout/stderr, su log
        # se volcaba sobre el prompt del usuario y moria al cerrar la terminal.
        APP_LOG="$BUILD_DIR/llamacode-launch.log"
        c_info "Launching LlamaCode... (log: $APP_LOG)"
        # La redireccion va sobre TODO el bloque en background: el bash que lo
        # corre espera a la app, y si conserva el stdout de la terminal la deja
        # colgada (curl | bash nunca termina).
        ( cd "$BUILD_DIR" && LD_LIBRARY_PATH="$QTDIR/lib:${LD_LIBRARY_PATH:-}"             setsid nohup "$EXE" ) >"$APP_LOG" 2>&1 </dev/null &
    else
        c_info "No display detected. Run later with:"
        echo "  LD_LIBRARY_PATH=$QTDIR/lib $EXE"
    fi
fi
