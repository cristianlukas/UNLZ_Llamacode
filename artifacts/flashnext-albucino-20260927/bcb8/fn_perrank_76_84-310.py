import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    # Generate simulated data for 100 people
    people = []
    for _ in range(PEOPLE_COUNT):
        name = f"Person_{random.randint(1000, 9999)}"
        age = random.randint(18, 80)
        height = round(random.uniform(150.0, 200.0), 2)  # in cm
        weight = round(random.uniform(45.0, 120.0), 2)   # in kg
        people.append([name, age, height, weight])
    
    # Calculate averages
    ages = [p[1] for p in people]
    heights = [p[2] for p in people]
    weights = [p[3] for p in people]
    
    avg_age = round(mean(ages), 2)
    avg_height = round(mean(heights), 2)
    avg_weight = round(mean(weights), 2)
    
    # Write to CSV file
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for person in people:
            writer.writerow(person)
        # Append averages row
        writer.writerow(['Average', avg_age, avg_height, avg_weight])
    
    return os.path.abspath(filename)
