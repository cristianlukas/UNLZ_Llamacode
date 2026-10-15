#!/usr/bin/env bash
# Packages a built LlamaCode binary as the Linux release asset.
#
#   scripts/package-linux.sh <tag> <build-dir> <qt-dir> [out-dir] [source-dir]
#
# source-dir (default: this checkout) is the tree whose qml/ and icons are used:
# the CI packages a tag with the scripts of the workflow's commit.
#
# Builds an AppDir with linuxdeploy + its Qt plugin (Qt libs, plugins and the
# QML modules the app imports, RPATH $ORIGIN/../lib) and tars it:
#
#   dist/LlamaCode-<tag>-linux-x64.tar.gz          (AppDir at the root: usr/bin/LlamaCode)
#   dist/LlamaCode-<tag>-linux-x64.tar.gz.sha256   ("<hex>  <name>")
#
# update-binary.sh extracts it as the install folder. Built on Ubuntu 24.04:
# needs glibc >= 2.39 on the target. Debug (vX.Y.Z-debug) is stripped by
# linuxdeploy like any other build; the channel comes from the tag.
set -euo pipefail

tag="${1:?tag}"; build="${2:?build dir}"; qtdir="${3:?qt dir}"; out="${4:-dist}"
[[ "$tag" =~ ^v([0-9]+\.[0-9]+\.[0-9]+)(-debug)?$ ]] || { echo "invalid tag: $tag" >&2; exit 1; }
version="${BASH_REMATCH[1]}"
channel=prod; [ -n "${BASH_REMATCH[2]}" ] && channel=debug

root="$(cd "${5:-$(dirname "$0")/..}" && pwd)"
build="$(cd "$build" && pwd)"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
exe="$build/LlamaCode"
[ -x "$exe" ] || { echo "built binary missing: $exe" >&2; exit 1; }

# linuxdeploy + Qt plugin pinned to a release tag and checked by SHA-256: they
# run inside the build whose output is then signed (attest-build-provenance),
# so they must be exactly what was reviewed. "continuous" changed under us.
# To update: pick the new tags, sha256sum the AppImages, re-run this locally
# and check the smoke test (offscreen + xcb) still passes.
LINUXDEPLOY_TAG="1-alpha-20251107-1"
LINUXDEPLOY_SHA256="c20cd71e3a4e3b80c3483cef793cda3f4e990aca14014d23c544ca3ce1270b4d"
PLUGIN_QT_TAG="1-alpha-20250213-1"
PLUGIN_QT_SHA256="15106be885c1c48a021198e7e1e9a48ce9d02a86dd0a1848f00bdbf3c1c92724"
tools="$out/.linuxdeploy"
mkdir -p "$tools"
fetch_tool() {   # fetch_tool FILE REPO TAG SHA256 (cached copy reused only if it matches)
    local f="$tools/$1"
    if [ ! -f "$f" ] || [ "$(sha256sum "$f" | cut -d' ' -f1)" != "$4" ]; then
        # Retries: a transient 504 from GitHub failed a whole CI run.
        curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors -o "$f" \
            "https://github.com/linuxdeploy/$2/releases/download/$3/$1"
    fi
    local got; got="$(sha256sum "$f" | cut -d' ' -f1)"
    [ "$got" = "$4" ] || { rm -f "$f"; echo "SHA-256 mismatch for $1 ($3): expected $4, got $got" >&2; exit 1; }
    chmod +x "$f"
}
fetch_tool linuxdeploy-x86_64.AppImage linuxdeploy "$LINUXDEPLOY_TAG" "$LINUXDEPLOY_SHA256"
fetch_tool linuxdeploy-plugin-qt-x86_64.AppImage linuxdeploy-plugin-qt "$PLUGIN_QT_TAG" "$PLUGIN_QT_SHA256"

appdir="$out/stage-linux"
rm -rf "$appdir"; mkdir -p "$appdir"
cat > "$out/llamacode.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=LlamaCode
Exec=LlamaCode
Icon=llamacode
Categories=Development;
EOF
icon="$root/assets/app_icon.png"; [ "$channel" = debug ] && icon="$root/assets/debug_icon.png"
cp "$icon" "$out/llamacode.png"

# The app only uses SQLite. linuxdeploy deploys EVERY sqldriver and dies on the
# ones whose client library is not installed (libmimerapi.so, libmysqlclient...):
# move them aside while it runs and put them back afterwards.
sqldrivers="$qtdir/plugins/sqldrivers"
parked="$out/.parked-sqldrivers"
restore_sqldrivers() { if [ -d "$parked" ]; then mv "$parked"/* "$sqldrivers"/ 2>/dev/null || true; rmdir "$parked"; fi; }
trap restore_sqldrivers EXIT
mkdir -p "$parked"
for f in "$sqldrivers"/*.so; do
    case "$(basename "$f")" in libqsqlite.so) ;; *) [ -e "$f" ] && mv "$f" "$parked"/ ;; esac
done

export APPIMAGE_EXTRACT_AND_RUN=1
export QMAKE="$qtdir/bin/qmake"
export QML_SOURCES_PATHS="$root/qml"
export LD_LIBRARY_PATH="$qtdir/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export EXTRA_QT_MODULES="svg;multimedia"
# By default only xcb is deployed: QT_QPA_PLATFORM=wayland (or offscreen, the app
# started without a display) then died with "no Qt platform plugin". With a
# wayland platform plugin the Qt plugin also deploys wayland-shell-integration,
# -decoration-client and -graphics-integration-client.
export EXTRA_PLATFORM_PLUGINS="libqoffscreen.so;libqwayland-generic.so;libqwayland-egl.so"
PATH="$tools:$PATH" "$tools/linuxdeploy-x86_64.AppImage" \
    --appdir "$appdir" -e "$exe" -d "$out/llamacode.desktop" -i "$out/llamacode.png" --plugin qt

# Qt.labs.settings is not always picked up by the QML scanner (same as Windows).
if [ -d "$qtdir/qml/Qt/labs/settings" ] && [ ! -d "$appdir/usr/qml/Qt/labs/settings" ]; then
    mkdir -p "$appdir/usr/qml/Qt/labs"
    cp -r "$qtdir/qml/Qt/labs/settings" "$appdir/usr/qml/Qt/labs/"
fi
# Plugin dirs the pinned Qt plugin does not deploy by itself: Wayland shell /
# decorations / EGL buffer integration (without them QT_QPA_PLATFORM=wayland
# fails or Qt Quick has no GL context) and networkinformation (QML network
# status). Copy them and let linuxdeploy bring their deps and set their RPATH.
extra_dirs=(wayland-shell-integration wayland-decoration-client wayland-graphics-integration-client networkinformation)
for d in "${extra_dirs[@]}"; do
    if [ -d "$qtdir/plugins/$d" ] && [ ! -d "$appdir/usr/plugins/$d" ]; then
        cp -r "$qtdir/plugins/$d" "$appdir/usr/plugins/"
        "$tools/linuxdeploy-x86_64.AppImage" --appdir "$appdir" --deploy-deps-only "$appdir/usr/plugins/$d"
    fi
done
for p in platforms/libqoffscreen.so platforms/libqwayland-generic.so "${extra_dirs[@]}"; do
    [ -e "$appdir/usr/plugins/$p" ] || { echo "Qt plugin missing from the package: $p" >&2; exit 1; }
done
cp "$out/llamacode.png" "$appdir/llamacode.png"

# Newest glibc symbol version any bundled ELF needs: update-binary.sh refuses
# to install on an older system (it would not start) instead of breaking it.
# (non-ELF files make objdump fail: ignored, not fatal under pipefail)
min_glibc="$( { find "$appdir" -type f \( -name '*.so*' -o -perm -u+x \) -print0 \
    | xargs -0 objdump -T 2>/dev/null || true; } | grep -o 'GLIBC_[0-9][0-9.]*' | sed 's/GLIBC_//' \
    | sort -uV | tail -1 || true)"
[ -n "$min_glibc" ] || { echo "could not compute the minimum glibc" >&2; exit 1; }
cat > "$appdir/llamacode-install.json" <<EOF
{
    "kind": "binary",
    "channel": "$channel",
    "version": "$version",
    "tag": "$tag",
    "platform": "linux-x64",
    "minGlibc": "$min_glibc"
}
EOF

name="LlamaCode-$tag-linux-x64.tar.gz"
tar -C "$appdir" -czf "$out/$name" .
( cd "$out" && sha256sum "$name" > "$name.sha256" )
echo "[OK] $out/$name ($(du -h "$out/$name" | cut -f1))"
cat "$out/$name.sha256"
