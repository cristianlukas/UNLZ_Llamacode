```python
import os
import csv
import random
from statistics import mean
# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100
def task_func(filename):
    first_names = ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana', 'Edward', 'Fiona', 'George', 'Hannah']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    data = []
    for _ in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 90)
        height = round(random.uniform(140, 200), 2)  # in cm
        weight = round(random.uniform(40, 120), 2)   # in kg
        data.append([name, age, height, weight])
    
    # Write data to CSV
    with open(filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(data)
    
    # Calculate averages
    ages = [row[1] for row in data]
    heights = [row[2] for row in data]
    weights = [row[3] for row in data]
    
    avg_age = mean(ages)
    avg_height = mean(heights)
    avg_weight = mean(weights)
    
    # Append averages to the file
    with open(filename, mode='a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Average', round(avg_age, 2), round(avg_height, 2), round(avg_weight, 2)])
    
    return filename