import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    my_list.append('12')
    
    # Sum the numbers in the list (ignoring non-numeric elements)
    total = sum(x for x in my_list if isinstance(x, (int, float)))
    
    # Find all CSV files in the directory
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = sorted(glob.glob(pattern))
    
    if not files:
        raise FileNotFoundError(f"No files found in the specified directory: {file_dir}")
    
    # Select the first 'total' files (or all if total is larger than available)
    selected_files = files[:int(total)]
    
    if not selected_files:
        raise FileNotFoundError(f"No files selected for concatenation")
    
    # Read and concatenate the selected CSV files
    dataframes = [pd.read_csv(f) for f in selected_files]
    result = pd.concat(dataframes, ignore_index=True)
    
    return result
