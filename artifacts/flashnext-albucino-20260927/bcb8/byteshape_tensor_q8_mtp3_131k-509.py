import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    # Read both files
    try:
        with open(file_path1, 'r', newline='') as f1:
            lines1 = f1.readlines()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise Exception(f"IO error reading {file_path1}: {e}")

    try:
        with open(file_path2, 'r', newline='') as f2:
            lines2 = f2.readlines()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise Exception(f"IO error reading {file_path2}: {e}")

    # Check for empty files
    if not lines1 or all(line.strip() == '' for line in lines1):
        raise ValueError("File 1 is empty")
    if not lines2 or all(line.strip() == '' for line in lines2):
        raise ValueError("File 2 is empty")

    # Use ndiff to compare lines
    diff_lines = list(ndiff(lines1, lines2))

    results = []
    line_num = 0
    for diff_line in diff_lines:
        line_num += 1
        if diff_line.startswith('  '):
            # No change
            content = diff_line[2:].rstrip('\n')
            results.append({
                'Line Number': line_num,
                'Status': ' ',
                'Content': content
            })
        elif diff_line.startswith('- '):
            # Line in first file but not second
            content = diff_line[2:].rstrip('\n')
            results.append({
                'Line Number': line_num,
                'Status': '-',
                'Content': content
            })
        elif diff_line.startswith('+ '):
            # Line in second file but not first
            content = diff_line[2:].rstrip('\n')
            results.append({
                'Line Number': line_num,
                'Status': '+',
                'Content': content
            })
        elif diff_line.startswith('? '):
            # Skip question mark lines (they indicate character-level differences)
            continue
        else:
            # Handle any other prefix
            content = diff_line[2:].rstrip('\n') if len(diff_line) > 2 else ''
            results.append({
                'Line Number': line_num,
                'Status': ' ',
                'Content': content
            })

    df = pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    return df
