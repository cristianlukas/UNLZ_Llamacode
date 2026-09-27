import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    def read_file_lines(file_path, delimiter, quotechar):
        try:
            with open(file_path, 'r', newline='') as f:
                reader = csv.reader(f, delimiter=delimiter, quotechar=quotechar)
                lines = [','.join(row) for row in reader]
            if not lines:
                raise ValueError("File is empty")
            return lines
        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"IO error: {e}")

    lines1 = read_file_lines(file_path1, delimiter, quotechar)
    lines2 = read_file_lines(file_path2, delimiter, quotechar)

    diff = list(ndiff(lines1, lines2))

    results = []
    line_num = 0
    for d in diff:
        if d.startswith('  '):
            line_num += 1
            results.append((line_num, ' ', d[2:]))
        elif d.startswith('- '):
            line_num += 1
            results.append((line_num, '-', d[2:]))
        elif d.startswith('+ '):
            results.append((line_num, '+', d[2:]))
        elif d.startswith('? '):
            pass
        else:
            pass

    df = pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    return df
