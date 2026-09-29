"""Grade Intelligence Adversarial v1 artifacts with the hidden graders.

The suite stores commands double-escaped ("\\n"), so `sh` sees one line and every
grader fails with a syntax error inside the app. Here: unescape, python -> python3,
run in a copy of the workspace. usage: adv_grade.py WS_DIR [WS_DIR...]
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
SUITE = pathlib.Path.home() / '.local/share/LlamaCode/LlamaCode/benchmarks/custom/intelligence_adversarial_v1.json'
tasks = json.loads(SUITE.read_text())['prompts']
for ws in sys.argv[1:]:
    ok = []; bad = []
    for t in tasks:
        cmd = t['acceptance']['commands'][0]['command'].replace('\\n', '\n').replace("python - <<'PY'", "python3 - <<'PY'")
        with tempfile.TemporaryDirectory() as td:
            for f in os.listdir(ws):
                if f.endswith('.py'): shutil.copy(os.path.join(ws, f), td)
            art = os.path.join(td, t['artifactFile'])
            if not os.path.exists(art): bad.append((t['id'], 'missing artifact')); continue
            r = subprocess.run(['bash', '-c', cmd], cwd=td, capture_output=True, text=True, timeout=60)
            (ok if r.returncode == 0 else bad).append(t['id'] if r.returncode == 0 else (t['id'], (r.stderr or r.stdout).strip().splitlines()[-1:]))
    print(json.dumps(dict(ws=ws, score=f'{len(ok)}/{len(tasks)}', passed=ok, failed=bad), ensure_ascii=False, indent=1))
