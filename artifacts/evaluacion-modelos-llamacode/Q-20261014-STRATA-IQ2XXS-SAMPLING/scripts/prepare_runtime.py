#!/usr/bin/env python3
"""Prepare isolated IQ2_XS 1M Strata and LlamaCode test profiles."""
import json
import pathlib
import shutil


TASK_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
SOURCE_RUNTIME = REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-IQ2XS-MISSING-MODALITIES/runtime/profiles"
SOURCE_CONFIG = REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-ISTA-NEEDLE-HAYSTACK/receipts/configs/context-1048576.json"
SOURCE_TASKFLOW = REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/Q-20261014-R9700-TASKFLOW/runtime/xdg-data/LlamaCode/LlamaCode/benchmarks/custom/qwen38_taskflow_ultra_ast_vs_sol_20261006.json"
PROFILE_DIR = TASK_ROOT / "runtime/profiles"
CONFIG_DIR = TASK_ROOT / "configs"


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("agent_profiles.json", "models.json", "persona_styles.json", "runtimes.json", "workspaces.json"):
        shutil.copy2(SOURCE_RUNTIME / name, PROFILE_DIR / name)

    source_launches = load(SOURCE_RUNTIME / "launches.json")
    launch = next(row for row in source_launches if row.get("id") == "q14-iq2xs-cu")
    launch = dict(launch)
    launch.update({
        "id": "q14-iq2xs-sampling-taskflow",
        "name": "EVAL · ASTRA IQ2_XS 1M · TaskFlow sampling",
        "alias": "iq2xs-sampling-eval",
        "reasoningBudget": 8192,
        "tags": ["Q-20261014-STRATA-IQ2XXS-SAMPLING", "TaskFlow ULTRA", "sampling A/B"],
    })
    dump(PROFILE_DIR / "launches.json", [launch])

    source_backends = load(SOURCE_RUNTIME / "backends.json")
    backend = dict(next(row for row in source_backends if row.get("id") == "q14-iq2xs-strata"))
    backend.update({
        "name": "ISTA IQ2_XS · Strata 0.1.41 · sampling eval",
        "cloudBaseUrl": "http://127.0.0.1:8352",
        "cloudCtx": 1048576,
        "port": 8352,
    })
    dump(PROFILE_DIR / "backends.json", [backend])
    dump(PROFILE_DIR / "harnesses.json", [])

    config = load(SOURCE_CONFIG)
    config["port"] = 8352
    config["host"] = "127.0.0.1"
    config["log"] = str(TASK_ROOT / "receipts/strata-engine.log")
    dump(CONFIG_DIR / "iq2xs-strata-1m.json", config)

    taskflow_path = TASK_ROOT / "runtime/data/LlamaCode/LlamaCode/benchmarks/custom/qwen38_taskflow_ultra_ast_vs_sol_20261006.json"
    taskflow_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_TASKFLOW, taskflow_path)

    scripts = TASK_ROOT / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "start-strata.sh").write_text("""#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=\"/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261014-STRATA-IQ2XXS-SAMPLING\"
STRATA_ROOT=\"/home/cristian/.cache/strata-flashnext-iq3xxs-eval-20261009/source\"
exec \"$STRATA_ROOT/.venv/bin/python\" \"$STRATA_ROOT/serve/server.py\" --engine strata --config \"$TASK_ROOT/configs/iq2xs-strata-1m.json\" --host 127.0.0.1 --port 8352
""", encoding="utf-8")
    (scripts / "start-llamacode-headless.sh").write_text("""#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=\"/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/artifacts/evaluacion-modelos-llamacode/Q-20261014-STRATA-IQ2XXS-SAMPLING\"
export LLAMACODE_CONTROL_PORT=8898
export LLAMACODE_PROFILES_DIR=\"$TASK_ROOT/runtime/profiles\"
export XDG_DATA_HOME=\"$TASK_ROOT/runtime/data\"
export XDG_CACHE_HOME=\"$TASK_ROOT/runtime/cache\"
export XDG_CONFIG_HOME=\"$TASK_ROOT/runtime/config\"
export LLAMACODE_EVAL_TEMPERATURE
export LLAMACODE_EVAL_SEED
cd \"/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode\"
exec \"/home/cristian/.cache/llamacode-sampling-eval/build_linux/LlamaCode\" --agent-daemon
""", encoding="utf-8")


if __name__ == "__main__":
    main()
