import pandas as pd
import csv
from difflib import ndiff
import io

def task_func(file_path1, file_path2, delimiter=',', quotechar='"'):
    """
    Compares two CSV files line by line and creates a difference report.
    
    Parameters:
    file_path1 (str): Path to the first CSV file
    file_path2 (str): Path to the second CSV file
    delimiter (str): CSV delimiter character
    quotechar (str): Character used to quote fields
    
    Returns:
    pd.DataFrame: DataFrame containing the difference report
    
    Raises:
    FileNotFoundError: If either file cannot be found
    ValueError: If either file is empty
    Exception: For other IO related errors
    """
    # Check if files exist
    if not file_path1 or not file_path2:
        raise FileNotFoundError("One or both file paths are empty")
    
    try:
        # Read files into lists of lines
        lines1 = []
        lines2 = []
        
        with open(file_path1, 'r', encoding='utf-8') as f1:
            lines1 = f1.readlines()
        
        with open(file_path2, 'r', encoding='utf-8') as f2:
            lines2 = f2.readlines()
        
        # Check for empty files
        if len(lines1) == 0 or len(lines2) == 0:
            raise ValueError("One or both files are empty")
        
        # Convert to lists of strings for comparison
        lines1_str = [line.rstrip('\n') for line in lines1]
        lines2_str = [line.rstrip('\n') for line in lines2]
        
        # Use difflib to find differences
        diff_list = list(ndiff(lines1_str, lines2_str))
        
        # Create DataFrame
        df = pd.DataFrame(diff_list, columns=['Line Number', 'Status', 'Content'])
        
        # Assign status based on diff type
        for i, diff in enumerate(diff_list):
            if diff == ' ':
                df.loc[i, 'Status'] = ' '
            elif diff == '-':
                df.loc[i, 'Status'] = '-'
            elif diff == '+':
                df.loc[i, 'Status'] = '+'
            else:
                # Handle other diff types (e.g., whitespace changes, etc.)
                df.loc[i, 'Status'] = ' '
        
        # Assign content based on status
        for i, diff in enumerate(diff_list):
            if diff == ' ':
                df.loc[i, 'Content'] = lines1_str[i]
            elif diff == '-':
                df.loc[i, 'Content'] = lines1_str[i]
            elif diff == '+':
                df.loc[i, 'Content'] = lines2_str[i]
            else:
                df.loc[i, 'Content'] = diff
        
        return df
    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception:
        raise