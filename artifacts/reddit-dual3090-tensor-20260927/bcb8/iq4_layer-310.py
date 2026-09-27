```python
import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    first_names = ['John', 'Jane', 'Michael', 'Emily', 'David', 'Sarah', 'Chris', 'Anna', 'Robert', 'Lisa']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    data = []
    for _ in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        height = round(random.uniform(140, 200), 2)
        weight = round(random.uniform(40, 120), 2)
        data.append([name, age, height, weight])
    
    with open(filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(data)
        
        ages = [row[1] for row in data]
        heights = [row[2] for row in data]
        weights = [row[3] for row in data]
        
        avg_age = round(mean(ages), 2)
        avg_height = round(mean(heights), 2)
        avg_weight = round(mean(weights), 2)
        
        writer.writerow(['Average', avg_age, avg_height, avg_weight])
    
    return filename