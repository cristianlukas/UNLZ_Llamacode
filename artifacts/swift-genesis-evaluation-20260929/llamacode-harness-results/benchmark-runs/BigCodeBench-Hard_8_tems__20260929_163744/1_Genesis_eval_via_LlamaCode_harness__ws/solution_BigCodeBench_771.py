import re
import os
from pathlib import Path
import csv

def task_func(directory: str, pattern: str = r'^(.*?)-\d+\.csv$') -> list:
    new_files = []
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return new_files
    regex = re.compile(pattern)
    seen = set()
    for filename in sorted(os.listdir(dir_path)):
        match = regex.match(filename)
        if match:
            new_name = match.group(1) + '.csv'
            if new_name in seen:
                continue
            seen.add(new_name)
            src = dir_path / filename
            dst = dir_path / new_name
            with open(src, 'r', newline='') as f_in:
                rows = list(csv.reader(f_in))
            with open(dst, 'w', newline='') as f_out:
                csv.writer(f_out).writerows(rows)
            new_files.append(new_name)
    return new_files
