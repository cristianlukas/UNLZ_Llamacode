import pandas as pd
import numpy as np
import itertools

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])
    
    # Determine the maximum length of tuples to know how many positions we need
    max_len = max(len(t) for t in data_list) if data_list else 0
    
    if max_len == 0:
        return pd.DataFrame(columns=['Mean Value'])
    
    # For each position, collect all numeric values
    means = []
    for i in range(max_len):
        values = []
        for t in data_list:
            if i < len(t):
                val = t[i]
                # Check if the value is numeric (int, float, but not bool)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    values.append(val)
        if values:
            means.append(np.mean(values))
        else:
            means.append(np.nan)
    
    # Create DataFrame
    index = [f'Position {i}' for i in range(max_len)]
    df = pd.DataFrame({'Mean Value': means}, index=index)
    return df
