#!/usr/bin/env python3
"""Create an isolated LlamaCode runtime that targets the installed SOL profile."""
import json
import pathlib
import shutil


TASK_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
PROFILE_ID = "c8d4f1a7-2b69-4e80-95c3-7a1d6f8b2045"
PLATFORM_BACKEND_ID = "2baf3292-033d-4a6c-9f84-ea13ae4aae3b"
TASKFLOW_ID = "qwen38_taskflow_ultra_ast_vs_sol_20261006"
SMOKE_ID = "llamacode_local_coding_smoke"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def main():
    source = REPO_ROOT / "profiles"
    profiles = TASK_ROOT / "runtime/profiles"
    profiles.mkdir(parents=True, exist_ok=True)
    names = ("agent_profiles.json", "backends.json", "harnesses.json",
             "models.json", "persona_styles.json", "runtimes.json",
             "workspaces.json")
    for name in names:
        shutil.copy2(source / name, profiles / name)

    launches = load(source / "launches.json")
    launch = next(row for row in launches if row.get("id") == PROFILE_ID)
    dump(profiles / "launches.json", [launch])

    backends = load(source / "backends.json")
    backend = next(row for row in backends if row.get("id") == PLATFORM_BACKEND_ID)
    backend.pop("managedServer", None)
    dump(profiles / "backends.json", [backend])

    data = TASK_ROOT / "runtime/data/LlamaCode/LlamaCode/benchmarks/custom"
    data.mkdir(parents=True, exist_ok=True)
    taskflow_src = (REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/"
                    "Q-20261014-R9700-TASKFLOW/runtime/xdg-data/LlamaCode/"
                    "LlamaCode/benchmarks/custom/"
                    f"{TASKFLOW_ID}.json")
    smoke_src = (REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/"
                 "Q-20261014-STRATA-IQ2XXS-SAMPLING/runtime/data/LlamaCode/"
                 "LlamaCode/benchmarks/custom/"
                 f"{SMOKE_ID}.json")
    shutil.copy2(taskflow_src, data / taskflow_src.name)
    shutil.copy2(smoke_src, data / smoke_src.name)
    shutil.copy2(REPO_ROOT / "artifacts/evaluacion-modelos-llamacode/"
                 "Q-20261014-STRATA-IQ2XXS-SAMPLING/scripts/run_taskflow.py",
                 TASK_ROOT / "scripts/run_taskflow.py")

    taskflow = load(data / taskflow_src.name)
    smoke = load(data / smoke_src.name)
    print(json.dumps({
        "profile_id": PROFILE_ID,
        "platform_backend_id": PLATFORM_BACKEND_ID,
        "cloud_context": backend.get("cloudCtx"),
        "taskflow_id": taskflow.get("id"),
        "taskflow_sha256": __import__("hashlib").sha256(
            (data / taskflow_src.name).read_bytes()).hexdigest(),
        "taskflow_prompts": len(taskflow.get("prompts", [])),
        "smoke_id": smoke.get("id"),
        "smoke_sha256": __import__("hashlib").sha256(
            (data / smoke_src.name).read_bytes()).hexdigest(),
        "smoke_prompts": len(smoke.get("prompts", [])),
        "production_profiles_modified": False,
    }, indent=2))


if __name__ == "__main__":
    main()
