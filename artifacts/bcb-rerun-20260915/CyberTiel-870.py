import pandas as pd
import numpy as np
import itertools


def task_func(data_list=[('a', 1, 2.1), ('b', 2, 3.2), ('c', 3, 4.3), ('d', 4, 5.4), ('e', 5, 6.5)]):
    if not data_list:
        return pd.DataFrame(columns=['Mean Value'])

    num_cols = max(len(t) for t in data_list)
    means = []
    for i in range(num_cols):
        values = []
        for t in data_list:
            if i < len(t):
                val = t[i]
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    values.append(val)
        means.append(np.mean(values) if values else np.nan)

    df = pd.DataFrame({'Mean Value': means},
                      index=[f'Position {i}' for i in range(num_cols)])
    return df