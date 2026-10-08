import pandas as pd
import numpy as np

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])
    
    # Determine the maximum number of positions (columns)
    max_positions = 0
    for item in data_list:
        if isinstance(item, list):
            max_positions = max(max_positions, len(item))
        else:
            max_positions = max(max_positions, len(item))
    
    if max_positions == 0:
        return pd.DataFrame(columns=['Mean Value'])
    
    # Initialize lists to store values for each position
    position_values = [[] for _ in range(max_positions)]
    
    # Iterate through each tuple/list in the data
    for item in data_list:
        if isinstance(item, list):
            for idx, val in enumerate(item):
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    position_values[idx].append(val)
        else:
            for idx, val in enumerate(item):
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    position_values[idx].append(val)
    
    # Calculate means for each position
    means = []
    for idx, values in enumerate(position_values):
        if values:
            means.append(np.mean(values))
        else:
            means.append(np.nan)
    
    # Create DataFrame
    df = pd.DataFrame({'Mean Value': means}, index=[f'Position {i}' for i in range(max_positions)])
    
    return df