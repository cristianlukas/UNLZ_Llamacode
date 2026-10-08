import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    # Generate random names
    first_names = ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    people_data = []
    
    for i in range(PEOPLE_COUNT):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        name = f"{first_name} {last_name}"
        
        age = random.randint(18, 85)
        height = round(random.uniform(140, 200), 1)  # cm
        weight = round(random.uniform(40, 120), 1)  # kg
        
        people_data.append([name, age, height, weight])
    
    # Calculate averages
    ages = [row[1] for row in people_data]
    heights = [row[2] for row in people_data]
    weights = [row[3] for row in people_data]
    
    avg_age = mean(ages)
    avg_height = mean(heights)
    avg_weight = mean(weights)
    
    # Append averages to data
    people_data.append(['Average', avg_age, avg_height, avg_weight])
    
    # Ensure directory exists
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(people_data)
    
    return filename