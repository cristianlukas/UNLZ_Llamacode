import csv
import os
from collections import Counter

# Constants
CSV_FILE_PATH = 'match_data.csv'

def create_test_csv(filename, content):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(content)

def setup_csv():
    content = [
        ['team', 'goals', 'penalties'],
        ['Team A', '2', '1'],
        ['Team B', '1', '2'],
        ['Team C', '3', '0']
    ]
    create_test_csv('test_data/test_case_2.csv', content)

def task_func(goals, penalties, csv_file_path=CSV_FILE_PATH):
    # Read the CSV file to get existing goals and penalties
    existing_goals = 0
    existing_penalties = 0
    
    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                existing_goals += int(row['goals'])
                existing_penalties += int(row['penalties'])
    
    # Calculate new totals
    new_goals = len(goals)
    new_penalties = len(penalties)
    
    # Update the counts in the Counter
    existing_counter = Counter()
    existing_counter.update(existing_goals)
    existing_counter.update(existing_penalties)
    
    # Combine existing and new counts
    total_counter = Counter()
    total_counter.update(existing_counter)
    total_counter.update(new_goals)
    total_counter.update(new_penalties)
    
    return total_counter