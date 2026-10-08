import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    # Ensure the directory exists
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Generate random data for 100 people
    first_names = ['James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 'Michael', 'Linda', 'David', 'Elizabeth']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    data = []
    for i in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        height = round(random.uniform(150, 200), 2)  # Height in cm
        weight = round(random.uniform(50, 120), 2)   # Weight in kg
        data.append([name, age, height, weight])
    
    # Calculate averages
    avg_age = mean([row[1] for row in data])
    avg_height = mean([row[2] for row in data])
    avg_weight = mean([row[3] for row in data])
    
    # Append averages to data
    data.append(['Average', round(avg_age, 2), round(avg_height, 2), round(avg_weight, 2)])
    
    # Write to CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        writer.writerows(data)
    
    return filename