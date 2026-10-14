import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def task_func(file_location, sheet_name):
    if not os.path.exists(file_location):
        raise FileNotFoundError(f"Excel file not found: {file_location}")

    try:
        df = pd.read_excel(file_location, sheet_name=sheet_name)
    except ValueError as exc:
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook.") from exc

    stats = {}
    for column in df.columns:
        values = pd.to_numeric(df[column], errors='coerce')
        stats[column] = {
            'mean': float(values.mean()),
            'std': float(np.std(values, ddof=0)),
        }

    fig, ax = plt.subplots()
    ax.bar(list(stats.keys()), [stats[column]['mean'] for column in stats])
    ax.set_title('Mean and Standard Deviation')
    ax.set_xlabel('Columns')
    ax.set_ylabel('Values')

    return stats, fig
