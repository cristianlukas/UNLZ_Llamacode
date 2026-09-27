```python
import os
import csv
import random
from statistics import mean

# Constants
COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth',
                   'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen',
                   'Christopher', 'Nancy', 'Daniel', 'Lisa', 'Matthew', 'Betty', 'Anthony', 'Margaret', 'Mark', 'Sandra',
                   'Donald', 'Ashley', 'Steven', 'Kimberly', 'Paul', 'Emily', 'Andrew', 'Donna', 'Joshua', 'Michelle',
                   'Kenneth', 'Carol', 'Kevin', 'Amanda', 'Brian', 'Dorothy', 'George', 'Melissa', 'Edward', 'Deborah']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
                  'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
                  'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
                  'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
                  'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter', 'Roberts']

    data = []
    for _ in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 90)
        height = round(random.uniform(140, 200), 2)  # cm
        weight = round(random.uniform(40, 120), 2)   # kg
        data.append([name, age, height, weight])

    with open(filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(data)

        # Calculate averages
        ages = [row[1] for row in data]
        heights = [row[2] for row in data]
        weights = [row[3] for row in data]

        avg_age = round(mean(ages), 2)
        avg_height = round(mean(heights), 2)
        avg_weight = round(mean(weights), 2)

        writer.writerow(['Average', avg_age, avg_height, avg_weight])

    return filename