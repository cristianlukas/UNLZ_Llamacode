#!/usr/bin/env bash
# Test de scripts/release.sh en un repo temporal con remote local y un `gh`
# falso que registra sus argumentos (nunca publica nada real).
set -euo pipefail

src="$(cd "$(dirname "$0")/.." && pwd)/scripts/release.sh"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
fails=0
check() { if eval "$1"; then echo "  PASS $2"; else echo "  FAIL $2"; fails=$((fails + 1)); fi; }

git init -q --bare "$work/remote.git"
git init -q -b main "$work/repo"
cd "$work/repo"
git config user.email t@t; git config user.name t
mkdir -p scripts bin
cp "$src" scripts/release.sh
printf 'cmake_minimum_required(VERSION 3.21)\nproject(LlamaCode VERSION 0.1.5 LANGUAGES CXX)\n' > CMakeLists.txt
git add . && git commit -q -m "base"
git remote add origin "$work/remote.git"
git push -q origin main
git tag -a v0.1.4-debug -m d && git commit -q --allow-empty -m "feat: cosa nueva"

cat > bin/gh <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "$GH_LOG"
EOF
chmod +x bin/gh
export PATH="$work/repo/bin:$PATH" GH_LOG="$work/gh.log"
echo "bin/" > .git/info/exclude

out="$(bash scripts/release.sh --channel debug)"
check '[[ "$out" == *"release v0.1.5-debug (debug)"* ]]' "dry run usa la version de CMakeLists"
check '[[ "$out" == *"desde   : v0.1.4-debug"* ]]' "notas desde el ultimo tag del mismo canal"
check '[[ "$out" == *"- feat: cosa nueva"* ]]' "incluye los commits nuevos"
check '[[ "$out" == *"[DRY RUN]"* ]] && ! git rev-parse -q --verify refs/tags/v0.1.5-debug >/dev/null' "dry run no taggea"

bash scripts/release.sh --channel debug --publish >/dev/null
check 'git ls-remote --tags origin | grep -q "refs/tags/v0.1.5-debug$"' "publish pushea el tag"
check 'grep -q "release create v0.1.5-debug --title LlamaCode 0.1.5 Debug .*--prerelease" "$GH_LOG"' "Debug sale como prerelease"

check '! bash scripts/release.sh --channel debug --publish >/dev/null 2>&1' "rechaza un tag que ya existe"

out="$(bash scripts/release.sh --bump --channel debug)"
check '[[ "$out" == *"0.1.5 -> 0.1.6"* ]] && grep -q "VERSION 0.1.5" CMakeLists.txt' "bump en dry run no toca CMakeLists"
bash scripts/release.sh --bump --channel debug --publish >/dev/null
check 'grep -q "VERSION 0.1.6" CMakeLists.txt' "bump sube el patch"
check '[ "$(git log -1 --pretty=%s)" = "Release v0.1.6 (Debug channel)" ]' "bump commitea"
check 'git ls-remote origin refs/heads/main | grep -q "$(git rev-parse HEAD)"' "bump pushea la rama"
check 'git ls-remote --tags origin | grep -q "refs/tags/v0.1.6-debug$"' "bump publica el tag nuevo"

git commit -q --allow-empty -m "despues del debug"
bash scripts/release.sh --promote --publish >/dev/null
check '[ "$(git rev-list -n1 v0.1.6)" = "$(git rev-list -n1 v0.1.6-debug)" ]' "promote taggea el mismo commit que el Debug"
check 'grep -q "release create v0.1.6 --title LlamaCode 0.1.6 Prod .*--latest" "$GH_LOG"' "promote publica Prod como latest"

echo "dirty" >> CMakeLists.txt
check '! bash scripts/release.sh --version 9.9.9 --publish >/dev/null 2>&1' "publish rechaza un arbol sucio"
git checkout -q CMakeLists.txt

if [ $fails -eq 0 ]; then echo "TODO OK"; exit 0; fi
echo "$fails FALLAS"; exit 1
