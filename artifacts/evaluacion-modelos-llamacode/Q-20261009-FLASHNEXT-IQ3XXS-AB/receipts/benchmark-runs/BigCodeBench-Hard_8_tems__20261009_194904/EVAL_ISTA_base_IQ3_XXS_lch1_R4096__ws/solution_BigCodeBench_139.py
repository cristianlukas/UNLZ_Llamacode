import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def task_func(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Input must be a non-empty DataFrame.")

    numeric_columns = df.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) == 0:
        raise ValueError("DataFrame must contain at least one numeric column.")

    common_axes = []
    for common_column in numeric_columns:
        common_fig, common_ax = plt.subplots()
        common_ax.hist(df[common_column].dropna())
        common_ax.set_title(common_column)
        common_ax.set_xlabel('Value')
        common_ax.set_ylabel('Frequency')
        common_axes.append(common_ax)

    return common_axes
