```python
import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list")
    
    # Add '12' to the list
    my_list = my_list + ['12']
    
    # Calculate the number of files to concatenate
    try:
        num_files = sum(my_list)
    except TypeError as e:
        raise TypeError(f"Cannot sum elements of my_list: {e}")
    
    # Find all CSV files in the directory
    pattern = os.path.join(file_dir, f'*{file_ext}')
    files = sorted(glob.glob(pattern))
    
    if not files:
        raise FileNotFoundError(f"No files found in the specified directory: {file_dir}")
    
    # Select the first num_files files (or all if fewer)
    selected_files = files[:num_files]
    
    if not selected_files:
        raise FileNotFoundError(f"No files selected for concatenation")
    
    # Read and concatenate the CSV files
    dataframes = []
    for file in selected_files:
        df = pd.read_csv(file)
        dataframes.append(df)
    
    if not dataframes:
        raise FileNotFoundError("No dataframes to concatenate")
    
    result_df = pd.concat(dataframes, ignore_index=True)
    
    return result_df