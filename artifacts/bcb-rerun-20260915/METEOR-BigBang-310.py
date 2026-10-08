import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    """
    Generates a CSV file containing simulated data for 100 people,
    including name, age, height, and weight. It also calculates and
    appends the average age, height, and weight at the end of the file.

    Args:
        filename (str): The path where the CSV file will be created.

    Returns:
        str: The path of the created CSV file.
    """
    # Generate simulated data for 100 people
    data = []
    for i in range(PEOPLE_COUNT):
        name = f"Person{i+1}"
        age = random.randint(1, 100)
        height = round(random.uniform(1.0, 2.5), 2)
        weight = round(random.uniform(30, 150), 2)
        data.append([name, age, height, weight])

    # Calculate averages
    avg_age = mean([row[1] for row in data])
    avg_height = mean([row[2] for row in data])
    avg_weight = mean([row[3] for row in data])

    # Write CSV file
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(data)
        writer.writerow(['Average', avg_age, avg_height, avg_weight])

    return filename