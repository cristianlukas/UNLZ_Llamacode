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
    
    names = []
    for i in range(PEOPLE_COUNT):
        first = random.choice(first_names)
        last = random.choice(last_names)
        names.append(f"{first} {last}")
    
    # Generate random ages (18-65)
    ages = [random.randint(18, 65) for _ in range(PEOPLE_COUNT)]
    
    # Generate random heights (140-190 cm)
    heights = [random.randint(140, 190) for _ in range(PEOPLE_COUNT)]
    
    # Generate random weights (40-120 kg)
    weights = [random.randint(40, 120) for _ in range(PEOPLE_COUNT)]
    
    # Create list of data rows
    data = []
    for i in range(PEOPLE_COUNT):
        data.append([names[i], ages[i], heights[i], weights[i]])
    
    # Calculate averages
    avg_age = mean(ages)
    avg_height = mean(heights)
    avg_weight = mean(weights)
    
    # Append averages as a single row
    data.append(['Average', round(avg_age), round(avg_height), round(avg_weight)])
    
    # Ensure directory exists
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Write to CSV file
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(data)
    
    return filename