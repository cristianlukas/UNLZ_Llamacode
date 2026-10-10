import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
def task_func(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Input must be a non-empty DataFrame.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        raise ValueError("DataFrame contains no numeric columns.")

    axes = []
    for col in numeric_cols:
        fig, ax = plt.subplots()
        ax.hist(df[col].dropna().values)
        ax.set_title(col)
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')
        axes.append(ax)
    return axes
