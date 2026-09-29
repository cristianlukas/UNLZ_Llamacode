import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def task_func(file_location, sheet_name):
    if not os.path.exists(file_location):
        raise FileNotFoundError(f"File not found: {file_location}")
    try:
        df = pd.read_excel(file_location, sheet_name=sheet_name)
    except ValueError:
        raise ValueError(f"Sheet not found: {sheet_name}")
    means = df.mean(numeric_only=True)
    stds = df.std(numeric_only=True)
    fig, ax = plt.subplots()
    x = np.arange(len(means))
    width = 0.4
    ax.bar(x - width/2, means.values, width, label='Mean')
    ax.bar(x + width/2, stds.values, width, label='Std')
    ax.set_title('Mean and Standard Deviation')
    ax.set_xlabel('Columns')
    ax.set_ylabel('Values')
    ax.set_xticks(x)
    ax.set_xticklabels(means.index)
    ax.legend()
    result = {'mean': means.to_dict(), 'std': stds.to_dict()}
    return result, fig
