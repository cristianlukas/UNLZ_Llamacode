import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    # Add '12' to the list
    my_list = my_list + ['12']
    
    # Calculate the sum of numbers in the list
    # Convert elements to numbers where possible
    total = 0
    for item in my_list:
        try:
            total += int(item)
        except (ValueError, TypeError):
            try:
                total += float(item)
            except (ValueError, TypeError):
                pass
    
    # Find all CSV files in the directory
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = sorted(glob.glob(pattern))
    
    if not files:
        raise FileNotFoundError(f"No files found in the specified directory: {file_dir}")
    
    # Concatenate the first 'total' files (or all if total > len(files))
    num_files = min(int(total), len(files))
    if num_files <= 0:
        raise FileNotFoundError(f"No files to concatenate (sum of list is {total})")
    
    dfs = []
    for file_path in files[:num_files]:
        dfs.append(pd.read_csv(file_path))
    
    if not dfs:
        raise FileNotFoundError(f"No files to concatenate")
    
    result = pd.concat(dfs, ignore_index=True)
    return result
