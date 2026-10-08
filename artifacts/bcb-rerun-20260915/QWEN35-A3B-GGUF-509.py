import pandas as pd
import csv
from difflib import ndiff

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    """
    Compare two CSV files and create a difference report.
    
    Args:
        file_path1: Path to the first CSV file.
        file_path2: Path to the second CSV file.
        delimiter: Delimiter used in the CSV files.
        quotechar: Quote character used in the CSV files.
        
    Returns:
        A pandas DataFrame with the differences.
        
    Raises:
        FileNotFoundError: If either of the files cannot be found.
        ValueError: If either of the files is empty.
        Exception: For other IO related errors.
    """
    # Check if files exist
    try:
        with open(file_path1, 'r', newline='', encoding='utf-8') as f1:
            pass
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path1}")
    except Exception as e:
        raise Exception(f"Error accessing file {file_path1}: {str(e)}")
        
    try:
        with open(file_path2, 'r', newline='', encoding='utf-8') as f2:
            pass
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path2}")
    except Exception as e:
        raise Exception(f"Error accessing file {file_path2}: {str(e)}")
    
    # Read files and check if they are empty
    try:
        with open(file_path1, 'r', newline='', encoding='utf-8') as f1:
            content1 = f1.read()
        if not content1.strip():
            raise ValueError(f"File is empty: {file_path1}")
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Error reading file {file_path1}: {str(e)}")
        
    try:
        with open(file_path2, 'r', newline='', encoding='utf-8') as f2:
            content2 = f2.read()
        if not content2.strip():
            raise ValueError(f"File is empty: {file_path2}")
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Error reading file {file_path2}: {str(e)}")
    
    # Split content into lines
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()
    
    # Use ndiff to compare lines
    diff = list(ndiff(lines1, lines2))
    
    # Process the diff results
    results = []
    line_number = 0
    
    for item in diff:
        if item.startswith('  '):
            # No change
            status = ' '
            content = item[2:]
            line_number += 1
        elif item.startswith('- '):
            # Line present in first file but not in second
            status = '-'
            content = item[2:]
            line_number += 1
        elif item.startswith('+ '):
            # Line present in second file but not in first
            status = '+'
            content = item[2:]
            # Don't increment line_number for lines only in second file
        elif item.startswith('? '):
            # Ignore question mark lines from ndiff
            continue
        else:
            # Other cases (shouldn't happen with ndiff)
            continue
            
        results.append({
            'Line Number': line_number if status != '+' else line_number,
            'Status': status,
            'Content': content
        })
        
    # Create DataFrame
    df = pd.DataFrame(results, columns=['Line Number', 'Status', 'Content'])
    
    return df