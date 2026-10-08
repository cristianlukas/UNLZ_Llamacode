#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:-Release}"
LC_CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/llamacode"
BUILD_DIR="${LC_TEST_BUILD_DIR:-$LC_CACHE_ROOT/build_tests_linux}"
QTVER="${LC_QTVER:-6.8.3}"
QTROOT="${LC_QTROOT:-$HOME/Qt}"
QTDIR="${LC_QTDIR:-$QTROOT/$QTVER/gcc_64}"

# qmlimportscanner y Ninja pueden quedar bloqueados al leer un checkout en
# NTFS montado. Los tests corren sobre una copia en filesystem nativo y el
# checkout Windows queda intacto.
SOURCE_ROOT="$ROOT_DIR"
 # With x-systemd.automount findmnt can report both the autofs wrapper and the
 # underlying NTFS mount. Use the last entry so the native-test decision is
 # based on the real filesystem.
SOURCE_FS="$(findmnt -T "$ROOT_DIR" -no FSTYPE 2>/dev/null | tail -n 1 || true)"
if [[ "$SOURCE_FS" == ntfs* || "$SOURCE_FS" == fuseblk ]]; then
    command -v rsync >/dev/null || { echo "Falta rsync para espejar el repo NTFS en la caché Linux." >&2; exit 2; }
    SOURCE_ROOT="$LC_CACHE_ROOT/source"
    mkdir -p "$SOURCE_ROOT"
    rsync -a --exclude='.git/' --exclude='.claude/' --exclude='build*/' \
        --exclude='work/' "$ROOT_DIR/" "$SOURCE_ROOT/"
    echo "Checkout NTFS detectado; usando copia nativa: $SOURCE_ROOT" >&2
fi

if [ ! -f "$QTDIR/lib/cmake/Qt6/Qt6Config.cmake" ]; then
    echo "Qt6 no encontrado en $QTDIR. Definí LC_QTDIR o ejecutá scripts/bootstrap.sh." >&2
    exit 2
fi
command -v cmake >/dev/null || { echo "Falta cmake." >&2; exit 2; }
command -v ninja >/dev/null || { echo "Falta ninja." >&2; exit 2; }

cmake -S "$SOURCE_ROOT" -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE="$CONFIG" \
    -DCMAKE_PREFIX_PATH="$QTDIR" \
    -DBUILD_TESTS=ON \
    -DLC_USE_QTKEYCHAIN=ON
cmake --build "$BUILD_DIR" --parallel "${LC_JOBS:-$(nproc)}"
QT_QPA_PLATFORM=offscreen QT_ASSUME_STDERR_HAS_CONSOLE=1 \
    ctest --test-dir "$BUILD_DIR" --output-on-failure --parallel "${LC_JOBS:-$(nproc)}"
