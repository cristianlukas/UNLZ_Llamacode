#!/usr/bin/env bash
# LlamaCode binary updater/installer for Linux (no compiler needed).
#
# Downloads the precompiled release asset (.tar.gz), verifies its SHA-256,
# waits for the running app to close, swaps the install folder (the old one is
# kept until the new one is in place), refreshes the menu entry and relaunches.
#
# "Actualizar" in the app writes this script (bundled in the qrc) to a temp file
# and runs it in a terminal with every option filled in. Standalone it works as
# an installer: without --asset-url it asks GitHub for the latest release.
#
#   update-binary.sh [--channel prod|debug] [--asset-url URL] [--sha256 HEX]
#                    [--sha256-url URL] [--install-dir DIR] [--version X.Y.Z]
#                    [--wait-pid PID] [--legacy-exe PATH]
#                    [--legacy-launcher PATH] [--no-launch]
#                    [--no-shortcuts] [--no-pause]
#
# Menu entry, autostart and relaunch go through <install>/llamacode, a launcher
# written here that clears a dev wrapper's Qt paths and sources
# ~/.config/llamacode/launcher.env (personal env: shared profiles, model roots;
# the app fills it from its own LLAMACODE_* vars the first time).
# --legacy-exe / --legacy-launcher: entries that started the old binary or a
# wrapper script now start that launcher.
#
# User data lives in ~/.local/share and ~/.config: never touched here.
set -euo pipefail

REPO="cristianlukas/UNLZ_Llamacode"
CHANNEL="${LC_CHANNEL:-prod}"
ASSET_URL="${LC_ASSET_URL:-}"
SHA256="${LC_SHA256:-}"
SHA256_URL="${LC_SHA256_URL:-}"
INSTALL_DIR="${LC_INSTALL_DIR:-}"
VERSION=""
WAIT_PID=0
LEGACY_EXE=""
LEGACY_LAUNCHER=""
NO_LAUNCH="${LC_NORUN:-}"
NO_SHORTCUTS=""
NO_PAUSE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --channel) CHANNEL="$2"; shift 2 ;;
        --asset-url) ASSET_URL="$2"; shift 2 ;;
        --sha256) SHA256="$2"; shift 2 ;;
        --sha256-url) SHA256_URL="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --wait-pid) WAIT_PID="$2"; shift 2 ;;
        --legacy-exe) LEGACY_EXE="$2"; shift 2 ;;
        --legacy-launcher) LEGACY_LAUNCHER="$2"; shift 2 ;;
        --no-launch) NO_LAUNCH=1; shift ;;
        --no-shortcuts) NO_SHORTCUTS=1; shift ;;
        --no-pause) NO_PAUSE=1; shift ;;
        *) echo "[ERROR] unknown option: $1" >&2; exit 2 ;;
    esac
done

LOG="${XDG_CACHE_HOME:-$HOME/.cache}/llamacode-update.log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee "$LOG") 2>&1

info() { printf '\033[36m[*] %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m[OK] %s\033[0m\n' "$*"; }
WORK=""
fail() {
    printf '\033[31m[ERROR] %s\033[0m\n' "$*"
    printf '        Log: %s\n' "$LOG"
    [ -n "$WORK" ] && rm -rf "$WORK"
    # Keep a terminal opened by the app readable.
    if [ -z "$NO_PAUSE" ] && [ -t 0 ]; then read -r -p "Press Enter to close" _ || true; fi
    exit 1
}

# Asset name contract, shared with the CI (release-binaries.yml) and the app
# (AppController::selectReleaseAsset): LlamaCode-<tag>-linux-x64.tar.gz, see
# resolve_latest below.

default_install_dir() {
    if [ "$1" = debug ]; then echo "$HOME/.local/opt/LlamaCode-Debug"; else echo "$HOME/.local/opt/LlamaCode"; fi
}

fetch() {   # fetch URL DEST [quiet]
    local url="$1" dest="$2"
    case "$url" in
        file://*) cp -f "${url#file://}" "$dest"; return ;;
        *://*) ;;
        *) if [ -f "$url" ]; then cp -f "$url" "$dest"; return; fi ;;
    esac
    if [ -n "${3:-}" ]; then curl -fsSL -o "$dest" "$url"
    else curl -fL --progress-bar -o "$dest" "$url"; fi
}

resolve_latest() {
    command -v python3 >/dev/null || fail "python3 is needed to read the GitHub release list."
    local json
    json="$(curl -fsSL -H 'Accept: application/vnd.github+json' \
        "https://api.github.com/repos/$REPO/releases?per_page=50")" || fail "Could not reach GitHub."
    # Prints: url<TAB>sha256(from digest, may be empty)<TAB>sha256url<TAB>version
    LC_JSON="$json" python3 -I - "$CHANNEL" <<'PY'
import json, os, re, sys
channel = sys.argv[1]
pat = re.compile(r'^v(\d+)\.(\d+)\.(\d+)-debug$' if channel == 'debug' else r'^v(\d+)\.(\d+)\.(\d+)$')
best = None
for r in json.loads(os.environ['LC_JSON']):
    if r.get('draft') or bool(r.get('prerelease')) != (channel == 'debug'):
        continue
    m = pat.match(r.get('tag_name', ''))
    if not m:
        continue
    name = 'LlamaCode-%s-linux-x64.tar.gz' % r['tag_name']
    assets = {a['name']: a for a in r.get('assets', [])}
    if name not in assets:
        continue
    ver = tuple(int(x) for x in m.groups())
    if best is None or ver > best[0]:
        a = assets[name]
        digest = a.get('digest') or ''
        sha = digest[7:] if digest.startswith('sha256:') else ''
        shaurl = assets.get(name + '.sha256', {}).get('browser_download_url', '')
        best = (ver, '\t'.join([a['browser_download_url'], sha, shaurl, '.'.join(map(str, ver))]))
if best:
    print(best[1])
PY
}

echo ""
printf '\033[35m=== LlamaCode update (precompiled binary) ===\033[0m\n'
[ "$CHANNEL" = prod ] || [ "$CHANNEL" = debug ] || fail "Invalid channel: $CHANNEL (prod|debug)"

# One update at a time (two clicks on "Actualizar").
LOCK="${XDG_RUNTIME_DIR:-/tmp}/llamacode-update.lock"
exec 9>"$LOCK"
if command -v flock >/dev/null && ! flock -n 9; then
    fail "Another LlamaCode update is already running. Wait for it to finish."
fi

if [ -z "$ASSET_URL" ]; then
    info "Looking up the latest $CHANNEL release on GitHub..."
    line="$(resolve_latest)"
    [ -n "$line" ] || fail "No $CHANNEL release with a Linux binary was found on GitHub."
    IFS=$'\t' read -r ASSET_URL d_sha d_shaurl d_ver <<<"$line"
    [ -n "$SHA256" ] || SHA256="$d_sha"
    [ -n "$SHA256_URL" ] || SHA256_URL="$d_shaurl"
    [ -n "$VERSION" ] || VERSION="$d_ver"
fi
[ -n "$INSTALL_DIR" ] || INSTALL_DIR="$(default_install_dir "$CHANNEL")"
INSTALL_DIR="${INSTALL_DIR%/}"
echo "Version : ${VERSION:-(unknown)} ($CHANNEL)"
echo "Install : $INSTALL_DIR"
echo "Source  : $ASSET_URL"
echo ""

# ---- Download + verify (nothing is touched until the hash matches) ---------
WORK="$(mktemp -d "${TMPDIR:-/tmp}/llamacode-update-XXXXXX")"
PKG="$WORK/LlamaCode.tar.gz"
info "Downloading..."
fetch "$ASSET_URL" "$PKG" || fail "Download failed: $ASSET_URL"
expected="$(printf '%s' "$SHA256" | grep -oiE '[0-9a-f]{64}' | head -1 | tr 'A-F' 'a-f' || true)"
if [ -z "$expected" ] && [ -n "$SHA256_URL" ]; then
    fetch "$SHA256_URL" "$WORK/asset.sha256" quiet || fail "Could not download the SHA-256 file."
    expected="$(grep -oiE '[0-9a-f]{64}' "$WORK/asset.sha256" | head -1 | tr 'A-F' 'a-f' || true)"
fi
[ -n "$expected" ] || fail "The release has no SHA-256 for this file; refusing to install an unverified binary."
actual="$(sha256sum "$PKG" | cut -d' ' -f1)"
[ "$actual" = "$expected" ] || fail "SHA-256 mismatch: expected $expected, got $actual. Nothing was changed."
ok "SHA-256 verified ($actual)"

# ---- Stage next to the target (same filesystem: the swap is a rename) ------
mkdir -p "$(dirname "$INSTALL_DIR")"
STAGING="$INSTALL_DIR.new"
rm -rf "$STAGING"; mkdir -p "$STAGING"
info "Extracting..."
tar -xzf "$PKG" -C "$STAGING" || { rm -rf "$STAGING"; fail "Could not extract the package."; }
[ -x "$STAGING/usr/bin/LlamaCode" ] || { rm -rf "$STAGING"; fail "The package has no usr/bin/LlamaCode."; }

# ---- Wait for the app, then swap -------------------------------------------
if [ "$WAIT_PID" -gt 0 ] 2>/dev/null && kill -0 "$WAIT_PID" 2>/dev/null; then
    info "Waiting for LlamaCode to close..."
    for _ in $(seq 1 120); do kill -0 "$WAIT_PID" 2>/dev/null || break; sleep 0.5; done
fi
# Only processes running FROM the install folder (app, scheduler daemon).
if command -v pgrep >/dev/null; then
    for pid in $(pgrep -f "^$INSTALL_DIR/usr/bin/LlamaCode" || true); do
        info "Closing LlamaCode (PID $pid)..."; kill "$pid" 2>/dev/null || true
    done
fi

OLD=""
if [ -e "$INSTALL_DIR" ]; then
    OLD="$INSTALL_DIR.old"
    rm -rf "$OLD"
    info "Replacing the install folder..."
    mv "$INSTALL_DIR" "$OLD"
fi
if ! mv "$STAGING" "$INSTALL_DIR"; then
    [ -n "$OLD" ] && [ ! -e "$INSTALL_DIR" ] && mv "$OLD" "$INSTALL_DIR"
    fail "Could not move the new version into place."
fi
[ -n "$OLD" ] && rm -rf "$OLD"
rm -rf "$WORK"; WORK=""
EXE="$INSTALL_DIR/usr/bin/LlamaCode"
LAUNCHER="$INSTALL_DIR/llamacode"
# Written on every update (the install folder was just replaced). Full path in
# the exec: the pgrep above finds running copies by their command line.
cat > "$LAUNCHER" <<'SH'
#!/usr/bin/env bash
# LlamaCode launcher (written by update-binary.sh on every update).
# Personal environment: ${XDG_CONFIG_HOME:-~/.config}/llamacode/launcher.env
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# A dev wrapper's Qt (LD_LIBRARY_PATH, plugin/QML paths) would shadow the
# bundled one when the app relaunches itself or is started from its terminal.
unset LD_LIBRARY_PATH QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QML2_IMPORT_PATH QML_IMPORT_PATH
env_file="${XDG_CONFIG_HOME:-$HOME/.config}/llamacode/launcher.env"
if [ -f "$env_file" ]; then set -a; . "$env_file"; set +a; fi
export LLAMACODE_LAUNCHER="$here/llamacode"
cd "$here/usr/bin" && exec "$here/usr/bin/LlamaCode" "$@"
SH
chmod +x "$LAUNCHER"
ok "Installed: $EXE"

if [ -z "$NO_SHORTCUTS" ]; then
    apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$apps"
    if [ "$CHANNEL" = debug ]; then id=llamacode-debug; title="LlamaCode Debug"; else id=llamacode; title="LlamaCode"; fi
    icon="$INSTALL_DIR/llamacode.png"
    entry="$apps/$id.desktop"
    # Same id as a hand-made entry (e.g. one that ran a dev wrapper): keep a copy.
    if [ -f "$entry" ] && ! grep -qF "$INSTALL_DIR/" "$entry"; then
        cp -f "$entry" "$entry.bak"
        info "Previous menu entry saved as $entry.bak"
    fi
    cat > "$entry" <<EOF
[Desktop Entry]
Type=Application
Name=$title
Comment=UNLZ LlamaCode
Exec="$LAUNCHER"
Path=$INSTALL_DIR/usr/bin
Icon=$icon
Terminal=false
Categories=Development;
EOF
    ok "Menu entry: $entry"
    # Entries (menu, autostart) that launched the OLD binary or wrapper now
    # launch the new install. Whole paths only: ~/.local/bin/llamacode must not
    # rewrite ~/.local/bin/llamacode-debug.
    for legacy in "$LEGACY_EXE" "$LEGACY_LAUNCHER"; do
        [ -n "$legacy" ] && [ "$legacy" != "$EXE" ] && [ "$legacy" != "$LAUNCHER" ] || continue
        for f in "$apps"/*.desktop "${XDG_CONFIG_HOME:-$HOME/.config}"/autostart/*.desktop; do
            [ -f "$f" ] && grep -qF "$legacy" "$f" || continue
            python3 -I - "$f" "$legacy" "$LAUNCHER" <<'PY' && ok "Now points to the new install: $f"
import re, sys
p, old, new = sys.argv[1:4]
s = open(p, encoding='utf-8').read()
t = re.sub(re.escape(old) + r'(?=["\'\s]|$)', lambda m: new, s, flags=re.M)
if t == s:
    sys.exit(1)
open(p, 'w', encoding='utf-8').write(t)
PY
        done
    done
fi

# Runtime tools the package cannot bundle (desktop automation, OCR, sandbox).
# The app starts without them; the matching features fail. Warn, don't block.
missing=""
for tool in ${LC_RUNTIME_TOOLS:-tesseract xdotool wmctrl bwrap}; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        missing="$missing $tool"
    elif [ "$tool" = tesseract ] && ! tesseract --list-langs 2>/dev/null | grep -qx spa; then
        # Spanish OCR is preferred (OcrEngine); English-only misreads the UI.
        missing="$missing tesseract-ocr-spa"
    fi
done
if [ -n "$missing" ]; then
    printf '\033[33m[!] Missing optional tools:%s\033[0m\n' "$missing"
    echo "    Computer use / OCR / sandboxed workers need them. On Ubuntu/Debian:"
    echo "    sudo apt install tesseract-ocr tesseract-ocr-spa xdotool wmctrl bubblewrap at-spi2-core x11-utils"
fi

if [ -z "$NO_LAUNCH" ]; then
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        info "Launching LlamaCode..."
        setsid nohup "$LAUNCHER" >/dev/null 2>&1 </dev/null &
    else
        info "No display detected. Run: $LAUNCHER"
    fi
fi
echo ""
ok "Update complete."
[ -z "$NO_PAUSE" ] && [ -t 0 ] && sleep 3
exit 0
