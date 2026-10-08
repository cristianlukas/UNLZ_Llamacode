import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("If 'my_list' is not a list.")
    
    count = sum(my_list)
    
    pattern = os.path.join(file_dir, f"*{file_ext}")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError("If no files are found in the specified directory.")
    
    dfs = [pd.read_csv(f) for f in files]
    result = pd.concat(dfs, ignore_index=True)
    return result