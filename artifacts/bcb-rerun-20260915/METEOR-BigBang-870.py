import pandas as pd
import numpy as np
import itertools

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])
    
    # Determine the maximum length of tuples
    max_len = max(len(t) for t in data_list)
    
    # Collect numerical values at each position
    position_values = [[] for _ in range(max_len)]
    for t in data_list:
        for i, val in enumerate(t):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                position_values[i].append(val)
    
    # Compute means, ignoring positions with no numerical values
    means = []
    for vals in position_values:
        if vals:
            means.append(np.mean(vals))
        else:
            means.append(np.nan)
    
    # Create DataFrame
    df = pd.DataFrame({'Mean Value': means}, index=[f'Position {i}' for i in range(len(means))])
    return df