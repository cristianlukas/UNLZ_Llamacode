import os
from pathlib import Path
import shutil
def task_func(kwargs, target_dir="non_none_files"):
    copied_files = []
    for file_path in kwargs:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy(file_path, target_dir)
            copied_files.append(os.path.join(target_dir, os.path.basename(file_path)))
    return copied_files
