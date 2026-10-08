import pandas as pd
import numpy as np
import itertools

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])
    
    max_len = 0
    for item in data_list:
        if isinstance(item, tuple):
            max_len = max(max_len, len(item))
        else:
            max_len = max(max_len, len(item))
    
    means = []
    for i in range(max_len):
        values = []
        for item in data_list:
            if isinstance(item, tuple):
                if i < len(item):
                    val = item[i]
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        values.append(val)
            else:
                if i < len(item):
                    val = item[i]
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        values.append(val)
        
        if values:
            mean_val = np.mean(values)
        else:
            mean_val = np.nan
        means.append(mean_val)
    
    index = [f'Position {i}' for i in range(max_len)]
    df = pd.DataFrame({'Mean Value': means}, index=index)
    return df