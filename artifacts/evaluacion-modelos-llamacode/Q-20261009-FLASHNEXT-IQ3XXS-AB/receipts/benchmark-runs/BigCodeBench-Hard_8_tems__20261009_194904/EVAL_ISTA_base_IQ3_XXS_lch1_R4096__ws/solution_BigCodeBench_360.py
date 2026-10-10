import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def task_func(file_location, sheet_name):
    if not os.path.exists(file_location):
        raise FileNotFoundError(f"Excel file not found: {file_location}")

    common_sheet_names = pd.ExcelFile(file_location).sheet_names
    if sheet_name not in common_sheet_names:
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook.")

    common_df = pd.read_excel(file_location, sheet_name=sheet_name)
    common_numeric_df = common_df.select_dtypes(include=[np.number])

    common_stats = {
        common_col: {
            'mean': common_numeric_df[common_col].mean(),
            'std': common_numeric_df[common_col].std()
        }
        for common_col in common_numeric_df.columns
    }

    common_labels = list(common_numeric_df.columns)
    common_means = [common_stats[c]['mean'] for c in common_labels]
    common_stds = [common_stats[c]['std'] for c in common_labels]

    common_fig, common_ax = plt.subplots()
    common_x = np.arange(len(common_labels))
    common_ax.bar(common_x - 0.2, common_means, width=0.4, label='Mean')
    common_ax.bar(common_x + 0.2, common_stds, width=0.4, label='Std Dev')
    common_ax.set_xticks(common_x)
    common_ax.set_xticklabels(common_labels)
    common_ax.set_title('Mean and Standard Deviation')
    common_ax.set_xlabel('Columns')
    common_ax.set_ylabel('Values')
    common_ax.legend()

    return common_stats, common_fig
