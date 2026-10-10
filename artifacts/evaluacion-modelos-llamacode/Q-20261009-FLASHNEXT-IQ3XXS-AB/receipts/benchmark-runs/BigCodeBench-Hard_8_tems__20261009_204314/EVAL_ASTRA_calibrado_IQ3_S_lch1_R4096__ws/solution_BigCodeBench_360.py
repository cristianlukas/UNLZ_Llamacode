import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
def task_func(file_location, sheet_name):
    if not os.path.exists(file_location):
        raise FileNotFoundError(f"The file {file_location} does not exist.")

    xl = pd.ExcelFile(file_location)
    if sheet_name not in xl.sheet_names:
        raise ValueError(f"Sheet '{sheet_name}' does not exist in the workbook.")

    data = xl.parse(sheet_name)
    numeric = data.select_dtypes(include=[np.number])

    stats = {}
    for col in numeric.columns:
        stats[col] = {
            'mean': float(numeric[col].mean()),
            'std': float(numeric[col].std(ddof=0)),
        }

    fig, ax = plt.subplots()
    ax.bar(numeric.columns.tolist(), [stats[c]['mean'] for c in numeric.columns])
    ax.set_title('Mean and Standard Deviation')
    ax.set_xlabel('Columns')
    ax.set_ylabel('Values')

    return stats, fig
