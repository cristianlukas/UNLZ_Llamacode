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
#                    [--no-shortcuts] [--no-pause] [--rollback]
#
# Menu entry, autostart and relaunch go through <install>/llamacode, a launcher
# written here that clears a dev wrapper's Qt paths and sources
# ~/.config/llamacode/launcher.env (personal env: shared profiles, model roots;
# the app fills it from its own LLAMACODE_* vars the first time).
# --legacy-exe / --legacy-launcher: entries that started the old binary or a
# wrapper script now start that launcher. Standalone, launcher.env is written
# from this shell's LLAMACODE_* vars; a menu entry that runs a hand-made wrapper
# setting LLAMACODE_* is left alone until launcher.env exists.
#
# Provenance: releases from ATTESTED_SINCE on carry a Sigstore attestation from
# release-binaries.yml. With the GitHub CLI logged in the package must verify
# against it (a hand-uploaded asset does not); without gh it is reported only.
# LC_REQUIRE_ATTESTATION=1 demands it whatever the version.
#
# Safety: refuses a package that needs a newer glibc than this system has
# (minGlibc in llamacode-install.json). The previous version stays as
# <install>.prev; if the new one dies with an error within LC_HEALTH_SECONDS
# (default 10) of the relaunch, it is put back and relaunched. --rollback does
# the same by hand, any time: the current version goes to <install>.failed and
# .prev comes back (same as update-binary.ps1 -Rollback).
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
ROLLBACK=""

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
        --rollback) ROLLBACK=1; shift ;;
        *) echo "[ERROR] unknown option: $1" >&2; exit 2 ;;
    esac
done

# The app writes this script to TMPDIR as llamacode-update-binary-<pid>.sh:
# remove that copy on the way out (a curl | bash run has no file to remove).
SELF_DELETE=""
case "$(basename -- "$0")" in
    llamacode-update-binary-*.sh) SELF_DELETE=1 ;;
esac

LOG="${XDG_CACHE_HOME:-$HOME/.cache}/llamacode-update.log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee "$LOG") 2>&1
TEE_PID=$!
# tee runs on its own: without waiting for it the last lines (the error that
# explains a failure) could still be unwritten when the terminal or a caller
# reads the output. Closing our ends gives it EOF.
on_exit() {
    [ -n "$SELF_DELETE" ] && rm -f -- "$0"
    exec 1>&- 2>&-
    wait "$TEE_PID" 2>/dev/null || true
}
trap on_exit EXIT

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
    if [ -n "${3:-}" ]; then curl -fsSL --retry 3 --retry-all-errors -o "$dest" "$url"
    else curl -fL --retry 3 --retry-all-errors --progress-bar -o "$dest" "$url"; fi
}

resolve_latest() {
    command -v python3 >/dev/null || fail "python3 is needed to read the GitHub release list."
    local json
    json="$(curl -fsSL --retry 3 --retry-all-errors -H 'Accept: application/vnd.github+json' \
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

write_launcher() {   # write_launcher DIR -- full path in the exec: pgrep finds running copies by it
    cat > "$1/llamacode" <<'SH'
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
    chmod +x "$1/llamacode"
}

stop_installed() {   # only processes running FROM that install folder (app, scheduler daemon)
    command -v pgrep >/dev/null || return 0
    local pid
    for pid in $(pgrep -f "^$1/usr/bin/LlamaCode" || true); do
        info "Closing LlamaCode (PID $pid)..."; kill "$pid" 2>/dev/null || true
    done
}

# <install>.prev back in place; the current one is kept as <install>.failed.
restore_previous() {
    [ -d "$1.prev" ] || fail "There is no previous version to go back to ($1.prev)."
    stop_installed "$1"
    rm -rf "$1.failed"
    if [ -e "$1" ]; then mv "$1" "$1.failed" || fail "Could not move $1 aside."; fi
    mv "$1.prev" "$1" || fail "Could not restore $1.prev."
    write_launcher "$1"   # a .prev from before the launcher existed has none
    ok "Previous version restored (the other one is kept in $1.failed)."
}

launch_detached() {   # 9>&-: the app must not inherit the update lock
    setsid nohup "$1" >"${2:-/dev/null}" 2>&1 </dev/null 9>&- &
}

if [ -n "$ROLLBACK" ]; then
    [ -n "$INSTALL_DIR" ] || INSTALL_DIR="$(default_install_dir "$CHANNEL")"
    INSTALL_DIR="${INSTALL_DIR%/}"
    info "Going back to the previous version in $INSTALL_DIR..."
    restore_previous "$INSTALL_DIR"
    if [ -z "$NO_LAUNCH" ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
        launch_detached "$INSTALL_DIR/llamacode"
    fi
    echo ""
    ok "Rollback complete."
    exit 0
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

# ---- Provenance (the hash only proves the download matches the release) ----
ATTESTED_SINCE="0.1.128"
version_ge() { [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" = "$2" ]; }
if { [ -n "$VERSION" ] && version_ge "$VERSION" "$ATTESTED_SINCE"; } || [ -n "${LC_REQUIRE_ATTESTATION:-}" ]; then
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
        info "Verifying build provenance..."
        if gh attestation verify "$PKG" --repo "$REPO" \
            --signer-workflow "$REPO/.github/workflows/release-binaries.yml" >"$WORK/attest.txt" 2>&1; then
            ok "Provenance verified: built by $REPO (release-binaries.yml)"
        else
            tail -5 "$WORK/attest.txt" | sed 's/^/        /'
            fail "Provenance check failed: this package was not built by the $REPO release workflow. Nothing was changed."
        fi
    elif [ -n "${LC_REQUIRE_ATTESTATION:-}" ]; then
        # Required means required: never fall back to the hash alone.
        fail "LC_REQUIRE_ATTESTATION is set but the provenance cannot be checked: install the GitHub CLI and run gh auth login. Nothing was changed."
    else
        printf '\033[33m[!] Provenance not verified (needs the GitHub CLI: gh auth login).\033[0m\n'
        echo "    The SHA-256 above only proves the download matches the release asset."
    fi
fi

# ---- Stage next to the target (same filesystem: the swap is a rename) ------
mkdir -p "$(dirname "$INSTALL_DIR")"
STAGING="$INSTALL_DIR.new"
rm -rf "$STAGING"; mkdir -p "$STAGING"
info "Extracting..."
tar -xzf "$PKG" -C "$STAGING" || { rm -rf "$STAGING"; fail "Could not extract the package."; }
[ -x "$STAGING/usr/bin/LlamaCode" ] || { rm -rf "$STAGING"; fail "The package has no usr/bin/LlamaCode."; }

# Built on a newer distro than this one: it would not even start. Refuse before
# touching the install (packages without minGlibc predate the check).
need_glibc="$(grep -oE '"minGlibc"[[:space:]]*:[[:space:]]*"[0-9.]+"' "$STAGING/llamacode-install.json" 2>/dev/null \
    | grep -oE '[0-9]+(\.[0-9]+)+' || true)"
have_glibc="${LC_GLIBC_VERSION:-$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}')}"
if [ -n "$need_glibc" ] && [ -n "$have_glibc" ] \
    && [ "$(printf '%s\n%s\n' "$need_glibc" "$have_glibc" | sort -V | head -1)" != "$need_glibc" ]; then
    rm -rf "$STAGING"
    fail "This build needs glibc >= $need_glibc and this system has $have_glibc (Ubuntu 24.04 or newer). Nothing was changed. Build from source instead: scripts/bootstrap.sh"
fi

write_launcher "$STAGING"

# ---- Wait for the app, then swap -------------------------------------------
if [ "$WAIT_PID" -gt 0 ] 2>/dev/null && kill -0 "$WAIT_PID" 2>/dev/null; then
    info "Waiting for LlamaCode to close..."
    for _ in $(seq 1 120); do kill -0 "$WAIT_PID" 2>/dev/null || break; sleep 0.5; done
fi
stop_installed "$INSTALL_DIR"

# The previous version is kept as .prev (one level): automatic rollback below,
# or by hand with --rollback.
OLD=""
if [ -e "$INSTALL_DIR" ]; then
    OLD="$INSTALL_DIR.prev"
    rm -rf "$OLD" "$INSTALL_DIR.old"
    info "Replacing the install folder..."
    mv "$INSTALL_DIR" "$OLD"
fi
if ! mv "$STAGING" "$INSTALL_DIR"; then
    [ -n "$OLD" ] && [ ! -e "$INSTALL_DIR" ] && mv "$OLD" "$INSTALL_DIR"
    fail "Could not move the new version into place."
fi
rm -rf "$WORK"; WORK=""
EXE="$INSTALL_DIR/usr/bin/LlamaCode"
LAUNCHER="$INSTALL_DIR/llamacode"
ok "Installed: $EXE"

# Standalone run from a shell that has the wrapper's vars: keep them for the
# launcher (the app does the same before running this). Never overwritten.
ENV_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/llamacode/launcher.env"
if [ ! -e "$ENV_FILE" ] && [ -n "$(compgen -e | grep '^LLAMACODE_' | grep -vx LLAMACODE_LAUNCHER || true)" ]; then
    mkdir -p "$(dirname "$ENV_FILE")"
    {
        echo "# LlamaCode launcher environment (from the LLAMACODE_* vars of the update)."
        echo "# Sourced with set -a; never overwritten by updates: edit freely."
        for k in $(compgen -e | grep '^LLAMACODE_' | grep -vx LLAMACODE_LAUNCHER | sort); do
            v="${!k}"; printf "%s='%s'\n" "$k" "${v//\'/\'\\\'\'}"
        done
    } > "$ENV_FILE"
    ok "Launcher environment saved: $ENV_FILE"
fi

# Exec target of a .desktop entry when it is a hand-made script that sets
# LLAMACODE_* (a dev wrapper), else empty.
wrapper_of() {
    local t
    t="$(sed -nE 's/^Exec="?([^" ]+)"?.*/\1/p' "$1" 2>/dev/null | head -1)"
    [ -n "$t" ] && [ -f "$t" ] && [ "$t" != "$LAUNCHER" ] || return 0
    case "$t" in "$INSTALL_DIR"/*) return 0 ;; esac
    head -c 2 "$t" | grep -q '#!' && grep -q 'LLAMACODE_' "$t" && echo "$t"
    return 0
}

if [ -z "$NO_SHORTCUTS" ]; then
    apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$apps"
    if [ "$CHANNEL" = debug ]; then id=llamacode-debug; title="LlamaCode Debug"; else id=llamacode; title="LlamaCode"; fi
    icon="$INSTALL_DIR/llamacode.png"
    entry="$apps/$id.desktop"
    wrapper="$(wrapper_of "$entry")"
    if [ -n "$wrapper" ] && [ ! -f "$ENV_FILE" ]; then
        # Replacing it would start the app WITHOUT the wrapper's environment
        # (shared profiles, model roots): leave the menu as it is.
        printf '\033[33m[!] %s runs %s, which sets LLAMACODE_* variables.\033[0m\n' "$entry" "$wrapper"
        echo "    Menu entry left unchanged. Copy those variables to $ENV_FILE"
        echo "    (KEY='value' lines) and run the update again to switch it to $LAUNCHER."
        SKIP_ENTRY=1
    else
        [ -n "$wrapper" ] && [ -z "$LEGACY_LAUNCHER" ] && LEGACY_LAUNCHER="$wrapper"
        SKIP_ENTRY=""
    fi
    # Same id as a hand-made entry (e.g. one that ran a dev wrapper): keep a copy.
    if [ -z "$SKIP_ENTRY" ] && [ -f "$entry" ] && ! grep -qF "$INSTALL_DIR/" "$entry"; then
        cp -f "$entry" "$entry.bak"
        info "Previous menu entry saved as $entry.bak"
    fi
    [ -n "$SKIP_ENTRY" ] || cat > "$entry" <<EOF
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
    [ -n "$SKIP_ENTRY" ] || ok "Menu entry: $entry"
    # Entries (menu, autostart) that launched the OLD binary or wrapper now
    # launch the new install. Whole paths only: ~/.local/bin/llamacode must not
    # rewrite ~/.local/bin/llamacode-debug.
    legacies=("$LEGACY_EXE")
    [ -n "$SKIP_ENTRY" ] || legacies+=("$LEGACY_LAUNCHER")
    for legacy in "${legacies[@]}"; do
        [ -n "$legacy" ] && [ "$legacy" != "$EXE" ] && [ "$legacy" != "$LAUNCHER" ] || continue
        for f in "$apps"/*.desktop "${XDG_CONFIG_HOME:-$HOME/.config}"/autostart/*.desktop; do
            [ -f "$f" ] && grep -qF "$legacy" "$f" || continue
            python3 -I - "$f" "$legacy" "$LAUNCHER" <<'PY' && ok "Now points to the new install: $f"
import re, sys
p, old, new = sys.argv[1:4]
s = open(p, encoding='utf-8').read()
end = r'(?=["\'\s]|$)'
# Quoted stays quoted; a bare path becomes quoted (the new one may have spaces).
t = re.sub(r'(?<=["\'])' + re.escape(old) + end, lambda m: new, s, flags=re.M)
t = re.sub(r'(?<![\w/"\'.-])' + re.escape(old) + end, lambda m: '"%s"' % new, t, flags=re.M)
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
        APP_LOG="${XDG_CACHE_HOME:-$HOME/.cache}/llamacode-first-run.log"
        launch_detached "$LAUNCHER" "$APP_LOG"
        app_pid=$!
        # A crash right after starting (missing lib/plugin, bad release) means
        # the update broke the app: put the previous version back. Exit 0 is
        # fine (e.g. it handed off to an instance that was already open).
        for _ in $(seq 1 $(( ${LC_HEALTH_SECONDS:-10} * 2 ))); do
            kill -0 "$app_pid" 2>/dev/null || break; sleep 0.5
        done
        if ! kill -0 "$app_pid" 2>/dev/null; then
            app_rc=0; wait "$app_pid" || app_rc=$?
            if [ "$app_rc" -ne 0 ]; then
                printf '\033[31m[ERROR] The new version exited with code %s right after starting.\033[0m\n' "$app_rc"
                tail -15 "$APP_LOG" 2>/dev/null | sed 's/^/        /'
                if [ -n "$OLD" ] && [ -d "$OLD" ]; then
                    info "Restoring the previous version..."
                    restore_previous "$INSTALL_DIR"
                    launch_detached "$LAUNCHER"
                fi
                fail "Update rolled back. App output: $APP_LOG"
            fi
        fi
    else
        info "No display detected. Run: $LAUNCHER"
    fi
fi
# Working update: a version that failed before is no longer worth ~180 MB.
rm -rf "$INSTALL_DIR.failed"
echo ""
ok "Update complete."
[ -z "$NO_PAUSE" ] && [ -t 0 ] && sleep 3
exit 0
