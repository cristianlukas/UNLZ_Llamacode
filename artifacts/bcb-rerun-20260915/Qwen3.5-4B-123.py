import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    num_files = sum(my_list)
    if num_files <= 0:
        return pd.DataFrame()
    
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError("No files found in the specified directory")
    
    dfs = [pd.read_csv(f) for f in files]
    result_df = pd.concat(dfs, ignore_index=True)
    return result_df