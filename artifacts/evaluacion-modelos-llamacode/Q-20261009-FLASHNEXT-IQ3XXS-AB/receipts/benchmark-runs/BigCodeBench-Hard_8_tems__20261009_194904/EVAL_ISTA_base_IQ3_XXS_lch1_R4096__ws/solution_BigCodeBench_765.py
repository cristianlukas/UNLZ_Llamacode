import os
from pathlib import Path
import shutil


def task_func(kwargs, target_dir="non_none_files"):
    copied_files = []
    for file_path in kwargs.values():
        if file_path is None:
            continue
        hold_file = Path(file_path)
        if hold_file.is_file() and os.stat(hold_file).st_size > 0:
            hold_file.parent.mkdir(parents=True, exist_ok=True)
            os.makedirs(target_dir, exist_ok=True)
            destination = shutil.copy(hold_file, target_dir)
            copied_files.append(destination)
    return copied_files
