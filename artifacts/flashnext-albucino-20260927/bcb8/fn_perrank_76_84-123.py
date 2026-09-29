import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    # Check if my_list is a list
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    # Add the element '12' to the list
    my_list.append('12')
    
    # Calculate the sum of numbers in the list
    # We need to convert elements to numbers, handling both int/float and string representations
    total = 0
    for item in my_list:
        if isinstance(item, (int, float)):
            total += item
        elif isinstance(item, str):
            try:
                total += float(item)
            except ValueError:
                raise ValueError(f"Cannot convert '{item}' to a number")
        else:
            raise ValueError(f"Cannot convert '{item}' to a number")
    
    # Get all CSV files in the directory
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = glob.glob(pattern)
    
    # Check if any files were found
    if not files:
        raise FileNotFoundError(f"No files found in directory: {file_dir}")
    
    # Sort files to have a deterministic order
    files.sort()
    
    # Determine how many files to concatenate
    num_files = int(total)
    
    # If num_files is 0 or negative, return an empty DataFrame
    if num_files <= 0:
        return pd.DataFrame()
    
    # Select the first num_files files
    selected_files = files[:num_files]
    
    # Read and concatenate DataFrames
    dfs = []
    for file in selected_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            raise e
    
    if not dfs:
        return pd.DataFrame()
    
    result = pd.concat(dfs, ignore_index=True)
    return result
