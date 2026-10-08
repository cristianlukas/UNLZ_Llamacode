import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100


def task_func(filename):
    # Generate random names
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer',
                   'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara',
                   'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah',
                   'Charles', 'Karen', 'Aisha', 'Wei', 'Priya', 'Omar', 'Mei']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
                  'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez',
                  'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas',
                  'Taylor', 'Moore', 'Jackson', 'Martin', 'Nguyen', 'Khan',
                  'Patel', 'Kim', 'Li']

    # Create data for each person
    data = []
    for _ in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(1, 100)
        height = round(random.uniform(150, 200), 2)
        weight = round(random.uniform(45, 120), 2)
        data.append([name, age, height, weight])

    # Write data to CSV file
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        writer.writerows(data)

        # Calculate and append averages
        avg_age = round(mean([row[1] for row in data]), 2)
        avg_height = round(mean([row[2] for row in data]), 2)
        avg_weight = round(mean([row[3] for row in data]), 2)
        writer.writerow(['Average', avg_age, avg_height, avg_weight])

    return filename