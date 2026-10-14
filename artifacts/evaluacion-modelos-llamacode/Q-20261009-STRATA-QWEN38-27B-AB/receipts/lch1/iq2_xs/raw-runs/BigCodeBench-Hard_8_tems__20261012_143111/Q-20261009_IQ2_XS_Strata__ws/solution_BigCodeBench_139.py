import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def task_func(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Input must be a non-empty DataFrame.")

    numeric_cols = df.select_dtypes(include=[np.number])
    if numeric_cols.shape[1] == 0:
        raise ValueError("DataFrame has no numeric columns.")

    axes = []
    for column in numeric_cols.columns:
        _, ax = plt.subplots()
        ax.hist(numeric_cols[column].dropna().values)
        ax.set_title(column)
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')
        axes.append(ax)

    return axes
