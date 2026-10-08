import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("'my_list' must be a list.")
    
    my_list.append('12')
    num_files = sum(int(x) for x in my_list)
    
    csv_files = glob.glob(os.path.join(file_dir, f'*{file_ext}'))
    if not csv_files:
        raise FileNotFoundError(f"No {file_ext} files found in '{file_dir}'.")
    
    selected_files = sorted(csv_files)[:num_files]
    
    if not selected_files:
        raise FileNotFoundError("No CSV files selected for concatenation.")
    
    dfs = [pd.read_csv(file) for file in selected_files]
    combined_df = pd.concat(dfs, ignore_index=True)
    
    return combined_df