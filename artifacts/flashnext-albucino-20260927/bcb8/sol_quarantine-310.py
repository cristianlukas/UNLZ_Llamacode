import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    people = []
    for i in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 90)
        height = round(random.uniform(140, 200), 2)  # cm
        weight = round(random.uniform(40, 120), 2)   # kg
        people.append([name, age, height, weight])
    
    # Write CSV
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(people)
        
        # Calculate averages
        avg_age = mean([p[1] for p in people])
        avg_height = mean([p[2] for p in people])
        avg_weight = mean([p[3] for p in people])
        
        # Append averages
        writer.writerow(['Average', round(avg_age, 2), round(avg_height, 2), round(avg_weight, 2)])
    
    return filename
