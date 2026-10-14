import re
import os
from pathlib import Path
import csv

def task_func(directory: str, pattern: str = r'^(.*?)-\d+\.csv$') -> list:
    new_files = []
    for entry in os.listdir(directory):
        if not entry.lower().endswith('.csv'):
            continue
        match = re.match(pattern, entry)
        if not match:
            continue
        new_name = match.group(1) + '.csv'
        source_path = Path(directory) / entry
        target_path = Path(directory) / new_name
        with open(source_path, 'r') as source_file:
            rows = list(csv.reader(source_file))
        with open(target_path, 'w') as target_file:
            writer = csv.writer(target_file)
            for row in rows:
                writer.writerow(row)
        new_files.append(new_name)
    return new_files
