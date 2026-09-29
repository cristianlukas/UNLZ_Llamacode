```python
import pandas as pd
import numpy as np
import itertools

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    if not data_list:
        return pd.DataFrame({'Mean Value': []}, index=pd.Index([], name='Position'))
    
    # Find the maximum length of any tuple
    max_len = max(len(t) for t in data_list)
    
    # For each position, collect all numeric values
    position_values = [[] for _ in range(max_len)]
    
    for t in data_list:
        for i in range(len(t)):
            val = t[i]
            # Check if value is numeric (int or float, but not bool)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                position_values[i].append(val)
    
    # Calculate means
    means = []
    for i in range(max_len):
        if position_values[i]:
            means.append(np.mean(position_values[i]))
        else:
            means.append(np.nan)
    
    # Create index
    index = [f'Position {i}' for i in range(max_len)]
    
    df = pd.DataFrame({'Mean Value': means}, index=pd.Index(index, name='Position'))
    
    return df