import pandas as pd
import os
import glob

def task_func(my_list, file_dir='./data_files/', file_ext='.csv'):
    """
    Modify a list by adding the element '12', then concatenate a number of CSV files 
    from a directory into a single DataFrame. The number of files concatenated is 
    determined by the sum of the numbers in the list.
    
    Parameters:
    my_list (list): A list of numbers.
    file_dir (str): The directory containing the CSV files.
    file_ext (str): The file extension of the CSV files.
    
    Returns:
    pd.DataFrame: A pandas DataFrame concatenating data from the selected CSV files.
    
    Raises:
    TypeError: If 'my_list' is not a list.
    FileNotFoundError: If no files are found in the specified directory.
    """
    # Check if my_list is a list
    if not isinstance(my_list, list):
        raise TypeError("my_list must be a list.")
    
    # Add '12' to the list
    my_list.append('12')
    
    # Calculate the number of files to concatenate
    num_files = sum(my_list)
    
    # Find all CSV files in the directory
    csv_files = glob.glob(os.path.join(file_dir, f'*{file_ext}'))
    
    # Check if any files were found
    if not csv_files:
        raise FileNotFoundError(f"No {file_ext} files found in {file_dir}.")
    
    # Sort the files to ensure consistent ordering
    csv_files.sort()
    
    # Select the required number of files
    selected_files = csv_files[:num_files]
    
    # Read and concatenate the CSV files
    dfs = [pd.read_csv(file) for file in selected_files]
    result_df = pd.concat(dfs, ignore_index=True)
    
    return result_df