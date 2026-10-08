import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    try:
        with open(file_path1, 'r', newline='', encoding='utf-8') as f1:
            lines1 = f1.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path1}")
    except Exception as e:
        raise Exception(f"IO error reading file 1: {e}")

    try:
        with open(file_path2, 'r', newline='', encoding='utf-8') as f2:
            lines2 = f2.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path2}")
    except Exception as e:
        raise Exception(f"IO error reading file 2: {e}")

    if not lines1:
        raise ValueError("First file is empty")
    if not lines2:
        raise ValueError("Second file is empty")

    # Normalize lines by stripping newline characters for comparison
    content1 = [line.rstrip('\n\r') for line in lines1]
    content2 = [line.rstrip('\n\r') for line in lines2]

    # Use ndiff to find differences
    diff = list(ndiff(content1, content2))

    result_rows = []
    max_line_num = max(len(content1), len(content2))

    for i in range(1, max_line_num + 1):
        line1 = content1[i-1] if i <= len(content1) else None
        line2 = content2[i-1] if i <= len(content2) else None

        if line1 is None and line2 is None:
            # Both files ended, no difference to report
            continue
        elif line1 is None:
            # Line only in second file
            status = '+'
            content = line2
        elif line2 is None:
            # Line only in first file
            status = '-'
            content = line1
        elif line1 == line2:
            # Same line, no difference
            continue
        else:
            # Different content in both files
            status = ' '
            content = f"{line1}\n{line2}"

        result_rows.append({
            'Line Number': i,
            'Status': status,
            'Content': content
        })

    df = pd.DataFrame(result_rows)
    return df