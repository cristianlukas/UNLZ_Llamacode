import os
from pathlib import Path
import shutil

def task_func(kwargs, target_dir="non_none_files"):
    copied_files = []
    os.makedirs(target_dir, exist_ok=True)
    for key, value in kwargs.items():
        if value is None:
            continue
        src = Path(value)
        if not src.exists():
            continue
        if src.is_file() and not src.stat().st_size:
            continue
        dest = Path(target_dir) / src.name
        shutil.copy2(str(src), str(dest))
        copied_files.append(str(dest))
    return copied_files
