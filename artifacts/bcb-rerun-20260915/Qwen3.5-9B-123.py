import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    file_count = sum(my_list)
    
    pattern = os.path.join(file_dir, '*' + file_ext)
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No {file_ext} files found in directory: {file_dir}")
    
    dataframes = []
    for file in files:
        df = pd.read_csv(file)
        dataframes.append(df)
    
    result_df = pd.concat(dataframes, ignore_index=True)
    return result_df