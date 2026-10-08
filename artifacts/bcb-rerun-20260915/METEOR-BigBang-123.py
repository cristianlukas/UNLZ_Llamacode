import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    my_list.append('12')
    num_files = sum(num for num in my_list if isinstance(num, (int, float)))
    files = sorted(glob.glob(os.path.join(file_dir, f'*{file_ext}')))
    if not files:
        raise FileNotFoundError(f"No {file_ext} files found in {file_dir}")
    selected_files = files[:num_files]
    dfs = [pd.read_csv(f) for f in selected_files]
    return pd.concat(dfs, ignore_index=True)