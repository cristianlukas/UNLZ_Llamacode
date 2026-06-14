#!/usr/bin/env bash
# LlamaCode zero-to-running bootstrap for Linux.
#
# Installs every dependency (git, cmake, ninja, g++, Qt6 + QML runtime modules),
# clones the repo into an isolated folder, builds and launches.
#
#   curl -fsSL https://raw.githubusercontent.com/guideahon/LlamaCode/main/scripts/bootstrap.sh | bash
#
# Override defaults via env vars:
#   LC_DIR=/path/to/install   (default: $HOME/LlamaCode)
#   LC_BRANCH=main
#   LC_CONFIG=Release         (Release|Debug)
#   LC_NORUN=1                (skip launching)

set -euo pipefail

REPO="https://github.com/guideahon/LlamaCode.git"
DIR="${LC_DIR:-$HOME/LlamaCode}"
BRANCH="${LC_BRANCH:-main}"
CONFIG="${LC_CONFIG:-Release}"

c_info() { printf '\033[36m[*] %s\033[0m\n' "$*"; }
c_ok()   { printf '\033[32m[OK] %s\033[0m\n' "$*"; }
c_die()  { printf '\033[31m[ERROR] %s\033[0m\n' "$*" >&2; exit 1; }

echo ""
printf '\033[35m=== LlamaCode bootstrap (Linux) ===\033[0m\n'
echo "Target: $DIR  branch=$BRANCH  config=$CONFIG"
echo ""

# ── Privilege escalation helper ──────────────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else
        c_die "Need root or sudo to install system packages."
    fi
fi

# ── Detect package manager + install deps ────────────────────────────────────
install_deps() {
    if command -v apt-get >/dev/null 2>&1; then
        c_info "Installing dependencies via apt..."
        $SUDO apt-get update -y
        $SUDO apt-get install -y --no-install-recommends \
            git cmake ninja-build build-essential pkg-config libgl1-mesa-dev \
            qt6-base-dev qt6-declarative-dev libqt6sql6-sqlite \
            qml6-module-qtquick qml6-module-qtquick-controls \
            qml6-module-qtquick-layouts qml6-module-qtquick-window \
            qml6-module-qtquick-templates qml6-module-qtqml-workerscript \
            qml6-module-qt-labs-settings || true
    elif command -v dnf >/dev/null 2>&1; then
        c_info "Installing dependencies via dnf..."
        $SUDO dnf install -y \
            git cmake ninja-build gcc-c++ make pkgconf-pkg-config mesa-libGL-devel \
            qt6-qtbase-devel qt6-qtdeclarative-devel
    elif command -v pacman >/dev/null 2>&1; then
        c_info "Installing dependencies via pacman..."
        $SUDO pacman -Sy --needed --noconfirm \
            git cmake ninja base-devel \
            qt6-base qt6-declarative
    elif command -v zypper >/dev/null 2>&1; then
        c_info "Installing dependencies via zypper..."
        $SUDO zypper install -y \
            git cmake ninja gcc-c++ pkg-config Mesa-libGL-devel \
            qt6-base-devel qt6-declarative-devel
    else
        c_die "Unsupported distro: install git, cmake, ninja, g++, and Qt6 (base + declarative) manually."
    fi
}
install_deps

command -v cmake >/dev/null 2>&1 || c_die "cmake not found after install."
command -v git   >/dev/null 2>&1 || c_die "git not found after install."
c_ok "dependencies"

# ── Clone / update ───────────────────────────────────────────────────────────
if [ -d "$DIR/.git" ]; then
    c_info "Repo exists -- pulling latest..."
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
GEN="Unix Makefiles"
command -v ninja >/dev/null 2>&1 && GEN="Ninja"

c_info "Configuring (generator: $GEN)..."
cmake -S "$DIR" -B "$BUILD_DIR" -G "$GEN" -DCMAKE_BUILD_TYPE="$CONFIG"

c_info "Building..."
cmake --build "$BUILD_DIR" --config "$CONFIG" -j "$(nproc)"

# Locate the binary (single- vs multi-config layouts).
EXE="$BUILD_DIR/LlamaCode"
[ -x "$EXE" ] || EXE="$BUILD_DIR/$CONFIG/LlamaCode"
[ -x "$EXE" ] || c_die "Built binary not found under $BUILD_DIR"

echo ""
c_ok "Done. Binary: $EXE"
echo ""

if [ -z "${LC_NORUN:-}" ]; then
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        c_info "Launching LlamaCode..."
        "$EXE" &
    else
        c_info "No display detected -- run it later with: $EXE"
    fi
fi
