import os
from pathlib import Path
import shutil

def task_func(kwargs, target_dir="non_none_files"):
    copied_files = []
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    for file_path, content in kwargs.items():
        if not content:
            continue
        path = Path(file_path)
        if not path.is_file():
            continue
        shutil.copy(str(path), target_dir)
        copied_files.append(str(Path(target_dir) / path.name))
    return copied_files
