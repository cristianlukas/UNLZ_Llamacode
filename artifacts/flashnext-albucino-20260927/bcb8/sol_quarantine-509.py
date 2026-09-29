import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    """
    Compare two CSV files and create a difference report.
    
    Parameters:
    file_path1 (str): Path to the first CSV file.
    file_path2 (str): Path to the second CSV file.
    delimiter (str): Delimiter character for CSV files.
    quotechar (str): Quote character for CSV files.
    
    Returns:
    DataFrame: A pandas DataFrame with the differences.
    
    Raises:
    FileNotFoundError: If either of the files cannot be found.
    ValueError: If either of the files is empty.
    Exception: For other IO related errors.
    """
    # Read both files
    try:
        with open(file_path1, 'r', newline='') as f1:
            lines1 = f1.readlines()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise Exception(f"Error reading file {file_path1}: {str(e)}")
    
    try:
        with open(file_path2, 'r', newline='') as f2:
            lines2 = f2.readlines()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise Exception(f"Error reading file {file_path2}: {str(e)}")
    
    # Check if files are empty
    if not lines1 or all(line.strip() == '' for line in lines1):
        raise ValueError(f"File {file_path1} is empty")
    if not lines2 or all(line.strip() == '' for line in lines2):
        raise ValueError(f"File {file_path2} is empty")
    
    # Use ndiff to compare the lines
    diff = ndiff(lines1, lines2)
    
    # Build the difference report
    results = []
    line_num = 0
    
    for line in diff:
        # Strip newline characters for comparison
        line_content = line.rstrip('\n').rstrip('\r')
        
        if line.startswith('  '):
            # No change
            line_num += 1
            results.append({
                'Line Number': line_num,
                'Status': ' ',
                'Content': line_content[2:]
            })
        elif line.startswith('- '):
            # Line in first file but not second
            line_num += 1
            results.append({
                'Line Number': line_num,
                'Status': '-',
                'Content': line_content[2:]
            })
        elif line.startswith('+ '):
            # Line in second file but not first
            results.append({
                'Line Number': line_num,
                'Status': '+',
                'Content': line_content[2:]
            })
        elif line.startswith('? '):
            # Skip these lines (they are for showing character-level differences)
            pass
    
    # Create DataFrame
    df = pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    
    return df
