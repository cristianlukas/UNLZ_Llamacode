import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    """
    Modifies a list by adding '12', concatenates CSV files from a directory 
    based on the sum of numbers in the list, and returns a DataFrame.
    
    Parameters:
    my_list (list): List of numbers to sum.
    file_dir (str): Directory path for CSV files.
    file_ext (str): Extension for CSV files.
    
    Returns:
    pd.DataFrame: Concatenated DataFrame from selected CSV files.
    
    Raises:
    TypeError: If 'my_list' is not a list.
    FileNotFoundError: If no files are found in the specified directory.
    """
    # Check if input is a list
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list.")
    
    # Add 12 to each element in the list
    modified_list = [str(x + 12) for x in my_list]
    
    # Calculate total number of files to concatenate
    total_files = sum(int(x) for x in modified_list)
    
    # Check if directory exists and find matching CSV files
    try:
        csv_files = glob.glob(os.path.join(file_dir, '**/*' + file_ext, recursive=True))
    except FileNotFoundError:
        raise FileNotFoundError("No files found in the specified directory.")
    
    # Check if any files were found
    if not csv_files:
        raise FileNotFoundError("No files found in the specified directory.")
    
    # Concatenate the CSV files into a DataFrame
    df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
    
    return df