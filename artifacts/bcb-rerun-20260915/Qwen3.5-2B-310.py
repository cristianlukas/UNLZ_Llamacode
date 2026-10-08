import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    # Ensure the directory exists
    dir_path = os.path.dirname(filename)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path)
    
    # Generate random data
    people = []
    for _ in range(PEOPLE_COUNT):
        name = f"Person {random.randint(1, 100)}"
        age = random.randint(18, 90)
        height = round(random.uniform(150, 200), 2)  # cm
        weight = round(random.uniform(50, 120), 2)  # kg
        people.append({
            'Name': name,
            'Age': age,
            'Height': height,
            'Weight': weight
        })
    
    # Write to CSV
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = COLUMNS
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(people)
    
    # Calculate and append average
    avg_age = mean([p['Age'] for p in people])
    avg_height = mean([p['Height'] for p in people])
    avg_weight = mean([p['Weight'] for p in people])
    
    with open(filename, 'a', newline='') as append_file:
        avg_data = f"\nAverage Age: {avg_age:.2f}\nAverage Height: {avg_height:.2f}\nAverage Weight: {avg_weight:.2f}"
        writer = csv.writer(append_file)
        writer.writerow([avg_data])
    
    return filename