import re
import os
from pathlib import Path
import csv


def task_func(directory: str, pattern: str = r'^(.*?)-\d+\.csv$') -> list:
    new_files = []
    for file_path in sorted(Path(directory).iterdir()):
        if not file_path.is_file():
            continue
        match = re.match(pattern, file_path.name)
        if not match:
            continue
        new_name = match.group(1) + '.csv'
        new_path = file_path.parent / new_name
        with open(file_path, 'r', newline='') as src:
            rows = list(csv.reader(src))
        with open(new_path, 'w', newline='') as dst:
            csv.writer(dst).writerows(rows)
        new_files.append(new_name)
    return new_files
