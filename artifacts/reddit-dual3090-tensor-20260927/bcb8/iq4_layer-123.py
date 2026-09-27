import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    # Add '12' to the list
    my_list.append('12')
    
    # Calculate the sum of numbers in the list
    # Convert elements to numbers where possible
    total = 0
    for item in my_list:
        try:
            total += int(item)
        except (ValueError, TypeError):
            pass
    
    # Find all CSV files in the directory
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = sorted(glob.glob(pattern))
    
    if not files:
        raise FileNotFoundError(f"No files found in {file_dir} with extension {file_ext}")
    
    # Select the first 'total' files (or all if total is larger than available)
    num_files = min(total, len(files))
    selected_files = files[:num_files]
    
    # Read and concatenate the CSV files
    dataframes = []
    for file_path in selected_files:
        df = pd.read_csv(file_path)
        dataframes.append(df)
    
    if not dataframes:
        raise FileNotFoundError(f"No files found in {file_dir} with extension {file_ext}")
    
    result = pd.concat(dataframes, ignore_index=True)
    return result
