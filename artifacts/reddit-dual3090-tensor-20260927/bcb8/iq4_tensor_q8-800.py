```python
import csv
import os
from collections import Counter

# Constants
CSV_FILE_PATH = 'match_data.csv'

def create_test_csv(filename, content):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(content)

# Example usage in a test setup:
def setup_csv():
    content = [
        ['team', 'goals', 'penalties'],
        ['Team A', '2', '1'],
        ['Team B', '1', '2'],
        ['Team C', '3', '0']
    ]
    create_test_csv('test_data/test_case_2.csv', content)

def task_func(goals, penalties, csv_file_path=CSV_FILE_PATH):
    # Initialize counter
    count = Counter()
    
    # Read existing CSV data if file exists
    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    count['goals'] += int(row['goals'])
                    count['penalties'] += int(row['penalties'])
                except (ValueError, KeyError):
                    pass
    
    # Add the given goals and penalties
    count['goals'] += goals
    count['penalties'] += penalties
    
    # Update the CSV file with the new totals
    # We'll write the updated totals as a single row or update existing rows?
    # The problem says "update it with the given goals and penalties"
    # This likely means we should write the new totals back to the file.
    # Let's write the updated totals as a new row or replace the file with the totals.
    # Since the input is just goals and penalties (not team names), we'll write a summary row.
    
    # Write the updated totals to the CSV file
    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['team', 'goals', 'penalties'])
        writer.writerow(['Total', count['goals'], count['penalties']])
    
    return count