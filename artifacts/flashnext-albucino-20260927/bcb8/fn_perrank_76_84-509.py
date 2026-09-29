import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    """
    Compare two CSV files line by line and create a difference report.
    
    Parameters:
    file_path1 (str): Path to the first CSV file.
    file_path2 (str): Path to the second CSV file.
    delimiter (str): The delimiter used in the CSV files.
    quotechar (str): The quote character used in the CSV files.
    
    Returns:
    DataFrame: A pandas DataFrame with the differences.
    
    Raises:
    FileNotFoundError: If either of the files cannot be found.
    ValueError: If either of the files is empty.
    Exception: For other IO related errors.
    """
    # Read lines from both files
    try:
        with open(file_path1, 'r', newline='') as f1:
            lines1 = f1.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path1}")
    except Exception as e:
        raise Exception(f"Error reading file {file_path1}: {e}")
    
    try:
        with open(file_path2, 'r', newline='') as f2:
            lines2 = f2.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path2}")
    except Exception as e:
        raise Exception(f"Error reading file {file_path2}: {e}")
    
    # Check if files are empty
    if not lines1:
        raise ValueError(f"File {file_path1} is empty.")
    if not lines2:
        raise ValueError(f"File {file_path2} is empty.")
    
    # Use ndiff to compare the lines
    diff = list(ndiff(lines1, lines2))
    
    # Build the report
    report = []
    line_num = 0
    for entry in diff:
        if entry.startswith(' '):
            # No change
            line_num += 1
            report.append({
                'Line Number': line_num,
                'Status': ' ',
                'Content': entry[1:].rstrip('\n\r')
            })
        elif entry.startswith('-'):
            # Line in file1 but not in file2
            line_num += 1
            report.append({
                'Line Number': line_num,
                'Status': '-',
                'Content': entry[1:].rstrip('\n\r')
            })
        elif entry.startswith('+'):
            # Line in file2 but not in file1
            # Note: ndiff doesn't increment line number for additions in the same way
            # We need to track line numbers properly
            # Actually, ndiff outputs lines from both files. For '+' lines, they come from file2.
            # The line number should correspond to the position in the combined diff output.
            # But the problem says "The line number in the file where the difference occurs."
            # This is ambiguous. Let's think about it differently.
            # 
            # Actually, looking at the problem statement more carefully:
            # "Line Number: The line number in the file where the difference occurs."
            # 
            # For '-' lines, it's the line number in file1.
            # For '+' lines, it's the line number in file2.
            # For ' ' lines, it's the line number in both files (they're the same).
            #
            # ndiff doesn't directly give us this. We need to track line numbers separately.
            # Let me reconsider the approach.
            pass
    
    # Let me redo this with proper line number tracking
    report = []
    line1_num = 0
    line2_num = 0
    
    for entry in diff:
        if entry.startswith(' '):
            # Same line in both files
            line1_num += 1
            line2_num += 1
            report.append({
                'Line Number': line1_num,  # or line2_num, they're the same
                'Status': ' ',
                'Content': entry[1:].rstrip('\n\r')
            })
        elif entry.startswith('-'):
            # Line only in file1
            line1_num += 1
            report.append({
                'Line Number': line1_num,
                'Status': '-',
                'Content': entry[1:].rstrip('\n\r')
            })
        elif entry.startswith('+'):
            # Line only in file2
            line2_num += 1
            report.append({
                'Line Number': line2_num,
                'Status': '+',
                'Content': entry[1:].rstrip('\n\r')
            })
    
    df = pd.DataFrame(report, columns=['Line Number', 'Status', 'Content'])
    return df
