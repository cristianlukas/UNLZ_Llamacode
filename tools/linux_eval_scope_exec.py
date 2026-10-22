"""Set the Linux OOM preference for one evaluation process, then exec it."""
from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> None:
    argv = sys.argv[1:]
    if argv[:1] == ["--"]:
        argv = argv[1:]
    if not argv:
        raise SystemExit("uso: linux_eval_scope_exec.py -- PROGRAMA [ARG ...]")
    try:
        score = int(os.environ.pop("LLAMACODE_EVAL_OOM_SCORE_ADJ", "900"))
    except ValueError as exc:
        raise SystemExit("LLAMACODE_EVAL_OOM_SCORE_ADJ debe ser entero") from exc
    if score < -1000 or score > 1000:
        raise SystemExit("LLAMACODE_EVAL_OOM_SCORE_ADJ debe estar entre -1000 y 1000")
    try:
        Path("/proc/self/oom_score_adj").write_text(f"{score}\n")
    except OSError as exc:
        raise SystemExit(f"No se pudo asignar oom_score_adj={score}: {exc}") from exc
    os.execvpe(argv[0], argv, os.environ)


if __name__ == "__main__":
    main()
