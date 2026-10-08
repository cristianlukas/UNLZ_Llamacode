import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    try:
        with open(file_path1, 'r', newline='', encoding='utf-8') as f1, \
             open(file_path2, 'r', newline='', encoding='utf-8') as f2:
            reader1 = csv.reader(f1, delimiter=delimiter, quotechar=quotechar)
            reader2 = csv.reader(f2, delimiter=delimiter, quotechar=quotechar)
            
            lines1 = [''.join(row) for row in reader1]
            lines2 = [''.join(row) for row in reader2]
            
            if not lines1 or not lines2:
                raise ValueError("One or both CSV files are empty")
    except FileNotFoundError:
        raise
    except IOError as e:
        raise Exception(f"IO error occurred: {str(e)}")
    
    diff = list(ndiff(lines1, lines2))
    
    results = []
    line_number = 0
    
    for line in diff:
        status = line[0]
        content = line[2:] if len(line) > 2 else ''
        
        if status == ' ':
            line_number += 1
        elif status == '-':
            line_number += 1
        elif status == '+':
            pass
        
        results.append({
            'Line Number': line_number,
            'Status': status if status != ' ' else ' ',
            'Content': content
        })
    
    df = pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    return df