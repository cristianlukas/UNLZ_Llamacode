import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    """
    Generates a CSV file containing simulated data for 100 people, including name, age, height, and weight.
    It also calculates and appends the average age, height, and weight at the end of the file.
    
    Args:
        filename (str): The path to the output CSV file.
        
    Returns:
        str: The path of the created CSV file.
    """
    # Generate simulated data for 100 people
    data = []
    for i in range(PEOPLE_COUNT):
        name = f"Person_{i+1}"
        age = random.randint(18, 70)
        height = round(random.uniform(150, 200), 2)  # Height in cm
        weight = round(random.uniform(50, 100), 2)    # Weight in kg
        data.append([name, age, height, weight])
    
    # Calculate averages
    ages = [row[1] for row in data]
    heights = [row[2] for row in data]
    weights = [row[3] for row in data]
    
    avg_age = round(mean(ages), 2)
    avg_height = round(mean(heights), 2)
    avg_weight = round(mean(weights), 2)
    
    # Append average row
    average_row = ['Average', avg_age, avg_height, avg_weight]
    data.append(average_row)
    
    # Write to CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(data)
    
    return filename