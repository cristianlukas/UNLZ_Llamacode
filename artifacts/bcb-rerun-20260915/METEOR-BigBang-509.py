import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    """
    Compare two CSV files line by line and provide a detailed report of differences.
    
    Parameters:
    file_path1 (str): Path to the first CSV file.
    file_path2 (str): Path to the second CSV file.
    delimiter (str): Delimiter used in the CSV files. Default is ','.
    quotechar (str): Quote character used in the CSV files. Default is '"'.
    
    Returns:
    DataFrame: A pandas DataFrame with columns 'Line Number', 'Status', 'Content'.
    
    Raises:
    FileNotFoundError: If either of the files cannot be found.
    ValueError: If either of the files is empty.
    Exception: For other IO related errors.
    """
    try:
        with open(file_path1, 'r', newline='') as f1, open(file_path2, 'r', newline='') as f2:
            reader1 = csv.reader(f1, delimiter=delimiter, quotechar=quotechar)
            reader2 = csv.reader(f2, delimiter=delimiter, quotechar=quotechar)
            
            rows1 = list(reader1)
            rows2 = list(reader2)
            
            if len(rows1) == 0 or len(rows2) == 0:
                raise ValueError("One or both files are empty.")
            
            # Convert rows to strings for comparison
            lines1 = [''.join(row) for row in rows1]
            lines2 = [''.join(row) for row in rows2]
            
            diff = list(ndiff(lines1, lines2))
            
            results = []
            line_num = 0
            for item in diff:
                if item.startswith('  '):
                    status = ' '
                    content = item[2:]
                elif item.startswith('- '):
                    status = '-'
                    content = item[2:]
                    line_num += 1
                elif item.startswith('+ '):
                    status = '+'
                    content = item[2:]
                    line_num += 1
                else:
                    continue
                results.append({'Line Number': line_num, 'Status': status, 'Content': content})
            
            return pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    
    except FileNotFoundError as e:
        raise FileNotFoundError(e)
    except ValueError as e:
        raise ValueError(e)
    except Exception as e:
        raise Exception(e)