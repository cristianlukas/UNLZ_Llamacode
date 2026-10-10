import re
import os
from pathlib import Path
import csv
def task_func(directory: str, pattern: str = r'^(.*?)-\d+\.csv$') -> list:
    new_files = []
    for filename in os.listdir(directory):
        match = re.match(pattern, filename)
        if match:
            new_filename = match.group(1) + '.csv'
            src_path = Path(directory) / filename
            dst_path = Path(directory) / new_filename
            with open(src_path, 'r') as src_file:
                rows = list(csv.reader(src_file))
            with open(dst_path, 'w') as dst_file:
                writer = csv.writer(dst_file)
                for row in rows:
                    writer.writerow(row)
            new_files.append(new_filename)
    return new_files
