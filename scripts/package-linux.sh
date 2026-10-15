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

tools="$out/.linuxdeploy"
mkdir -p "$tools"
for t in linuxdeploy-x86_64.AppImage linuxdeploy-plugin-qt-x86_64.AppImage; do
    if [ ! -x "$tools/$t" ]; then
        repo="linuxdeploy"; [[ "$t" == *plugin-qt* ]] && repo="linuxdeploy-plugin-qt"
        curl -fsSL -o "$tools/$t" "https://github.com/linuxdeploy/$repo/releases/download/continuous/$t"
        chmod +x "$tools/$t"
    fi
done

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
# The Qt plugin deploys wayland-shell-integration/-decoration-client but not the
# EGL buffer integration (without it Qt Quick on Wayland falls back to software
# or fails to get a GL context): copy it and let linuxdeploy bring its deps and
# set its RPATH.
gfx="wayland-graphics-integration-client"
if [ -d "$qtdir/plugins/$gfx" ] && [ ! -d "$appdir/usr/plugins/$gfx" ]; then
    cp -r "$qtdir/plugins/$gfx" "$appdir/usr/plugins/"
    "$tools/linuxdeploy-x86_64.AppImage" --appdir "$appdir" --deploy-deps-only "$appdir/usr/plugins/$gfx"
fi
for p in platforms/libqoffscreen.so platforms/libqwayland-generic.so wayland-shell-integration "$gfx"; do
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
