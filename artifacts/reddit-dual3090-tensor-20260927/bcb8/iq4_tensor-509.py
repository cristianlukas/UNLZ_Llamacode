import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
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
    
    if not lines1 or not lines2:
        raise ValueError("One or both files are empty")
    
    # Strip trailing newlines for comparison
    lines1_clean = [line.rstrip('\n\r') for line in lines1]
    lines2_clean = [line.rstrip('\n\r') for line in lines2]
    
    # Use ndiff to get the differences
    diff_lines = list(ndiff(lines1_clean, lines2_clean))
    
    results = []
    for line in diff_lines:
        if line.startswith('  '):
            # No change
            content = line[2:]
            results.append((' ', content))
        elif line.startswith('- '):
            # Line in first file but not second
            content = line[2:]
            results.append(('-', content))
        elif line.startswith('+ '):
            # Line in second file but not first
            content = line[2:]
            results.append(('+', content))
        elif line.startswith('? '):
            # Inline difference marker, skip these
            continue
        else:
            # Should not happen, but handle gracefully
            continue
    
    # Assign line numbers
    # We need to track line numbers properly
    # Let's redo this with proper line number tracking
    
    results = []
    line_num = 1
    i = 0
    j = 0
    
    # We'll use a simpler approach: iterate through ndiff output and track line numbers
    # ndiff gives us lines with prefixes. We need to map them to line numbers.
    # Let's use a different approach: use SequenceMatcher for more control
    
    from difflib import SequenceMatcher
    
    matcher = SequenceMatcher(None, lines1_clean, lines2_clean)
    results = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                results.append((i1 + k + 1, ' ', lines1_clean[i1 + k]))
        elif tag == 'delete':
            for k in range(i2 - i1):
                results.append((i1 + k + 1, '-', lines1_clean[i1 + k]))
        elif tag == 'insert':
            for k in range(j2 - j1):
                results.append((j1 + k + 1, '+', lines2_clean[j1 + k]))
        elif tag == 'replace':
            # For replace, we show all lines from both files
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                if k < (i2 - i1):
                    results.append((i1 + k + 1, '-', lines1_clean[i1 + k]))
                if k < (j2 - j1):
                    results.append((j1 + k + 1, '+', lines2_clean[j1 + k]))
    
    # Create DataFrame
    if not results:
        df = pd.DataFrame(columns=['Line Number', 'Status', 'Content'])
    else:
        df = pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    
    return df
