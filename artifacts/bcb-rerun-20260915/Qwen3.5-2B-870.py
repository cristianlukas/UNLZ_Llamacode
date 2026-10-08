import pandas as pd
import numpy as np
import itertools

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    """
    Calculate the mean of numerical values in each position across tuples in a list.
    Non-numeric values are ignored, and means are computed only from available data.
    Missing data in some of the tuples is simply ignored.
    
    Parameters:
    data_list (list of tuples): List of tuples containing mixed data types.
    
    Returns:
    pandas.DataFrame: DataFrame with 'Mean Value' column and index 'Position i'.
    """
    if not data_list:
        return pd.DataFrame()
    
    # Extract all numeric values from the list
    all_values = []
    for pos, tuple_item in enumerate(data_list):
        for val in tuple_item:
            if isinstance(val, (int, float)):
                all_values.append(val)
    
    # Calculate means for each position
    means = []
    for pos, tuple_item in enumerate(data_list):
        # Filter only numeric values for this position
        numeric_values = [v for v in tuple_item if isinstance(v, (int, float))]
        if len(numeric_values) > 0:
            mean_val = np.mean(numeric_values)
        else:
            mean_val = np.nan
        
        means.append(mean_val)
    
    # Create DataFrame
    df = pd.DataFrame(means, index=range(len(data_list)))
    df.columns = ['Mean Value']
    
    return df