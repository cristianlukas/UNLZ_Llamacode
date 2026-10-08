import pandas as pd
import numpy as np
import itertools

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    """
    Calculate the mean of numerical values in each position across tuples in a list.
    
    Parameters:
    data_list (list): A list of tuples containing mixed data types.
    
    Returns:
    DataFrame: A pandas DataFrame with the mean values of the numerical data at each position.
    """
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])
    
    # Determine the maximum length of the tuples
    max_len = max(len(t) for t in data_list)
    
    # Initialize a list to hold numerical values for each position
    position_values = [[] for _ in range(max_len)]
    
    # Iterate over each tuple and each position
    for t in data_list:
        for i, val in enumerate(t):
            if i < max_len:
                # Check if the value is numeric (int or float, but not bool)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    position_values[i].append(val)
    
    # Calculate the mean for each position
    means = []
    for vals in position_values:
        if vals:
            means.append(np.mean(vals))
        else:
            means.append(np.nan)
    
    # Create a DataFrame with the means
    df = pd.DataFrame(means, columns=['Mean Value'])
    df.index = [f'Position {i}' for i in range(len(means))]
    
    return df