import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    my_list.append('12')
    total_files = sum(my_list)
    
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = sorted(glob.glob(pattern))
    
    if not files:
        raise FileNotFoundError("No files found in the specified directory")
        
    num_files = min(total_files, len(files)) # Or just take total_files, but if total_files > len(files), it might fail. The problem says "The number of files concatenated is determined by the sum of the numbers in the list." It probably assumes the directory has enough files, or we should just take the first `total_files` files. Let's assume it's exactly `total_files` or we can just slice `files[:total_files]`.
    
    dfs = [pd.read_csv(f) for f in files[:total_files]]
    return pd.concat(dfs, ignore_index=True)