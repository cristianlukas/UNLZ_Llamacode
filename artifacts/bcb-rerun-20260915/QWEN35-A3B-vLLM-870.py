import pandas as pd
import numpy as np

def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5]):
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])
    
    max_len = max(len(t) for t in data_list)
    means = []
    for i in range(max_len):
        vals = []
        for t in data_list:
            if i < len(t):
                v = t[i]
                if isinstance(v, (int, float)):
                    vals.append(v)
        if vals:
            means.append(np.mean(vals))
        else:
            means.append(np.nan)
            
    df = pd.DataFrame({'Mean Value': means}, index=[f'Position {i}' for i in range(max_len)])
    return df