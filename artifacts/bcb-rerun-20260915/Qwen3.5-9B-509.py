import pandas as pd
import csv
from difflib import ndiff
import io

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    try:
        with open(file_path1, 'r', newline='', encoding='utf-8') as f1:
            reader1 = csv.reader(f1, delimiter=delimiter, quotechar=quotechar)
            lines1 = [line for line in reader1]
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path1}")
    except Exception as e:
        raise Exception(f"IO error reading {file_path1}: {str(e)}")

    try:
        with open(file_path2, 'r', newline='', encoding='utf-8') as f2:
            reader2 = csv.reader(f2, delimiter=delimiter, quotechar=quotechar)
            lines2 = [line for line in reader2]
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path2}")
    except Exception as e:
        raise Exception(f"IO error reading {file_path2}: {str(e)}")

    if len(lines1) == 0:
        raise ValueError("First file is empty.")
    if len(lines2) == 0:
        raise ValueError("Second file is empty.")

    # Use ndiff to compare lines
    diff = list(ndiff(lines1, lines2))
    
    result_rows = []
    for i, line in enumerate(diff):
        if line.startswith('- '):
            line_content = line[2:]
            result_rows.append({
                'Line Number': i + 1,
                'Status': '-',
                'Content': line_content
            })
        elif line.startswith('+ '):
            line_content = line[2:]
            result_rows.append({
                'Line Number': i + 1,
                'Status': '+',
                'Content': line_content
            })
        elif line.startswith('  '):
            line_content = line[2:]
            result_rows.append({
                'Line Number': i + 1,
                'Status': ' ',
                'Content': line_content
            })
        # Ignore lines starting with '?' (context lines in some diff implementations, though ndiff doesn't produce them)

    if not result_rows:
        # If no differences found but files are not empty, we still return an empty DataFrame with correct schema
        # However, the problem implies we report differences. If no differences, return empty DF.
        df = pd.DataFrame(columns=['Line Number', 'Status', 'Content'])
        return df

    df = pd.DataFrame(result_rows)
    return df