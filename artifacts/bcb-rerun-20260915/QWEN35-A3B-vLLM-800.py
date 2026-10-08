import csv
import os
from collections import Counter

CSV_FILE_PATH = 'match_data.csv'

def task_func(goals, penalties, csv_file_path=CSV_FILE_PATH):
    total_goals = 0
    total_penalties = 0
    
    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    total_goals += int(row['goals'])
                    total_penalties += int(row['penalties'])
                except (ValueError, KeyError):
                    pass
                    
    total_goals += goals
    total_penalties += penalties
    
    return Counter({'goals': total_goals, 'penalties': total_penalties})