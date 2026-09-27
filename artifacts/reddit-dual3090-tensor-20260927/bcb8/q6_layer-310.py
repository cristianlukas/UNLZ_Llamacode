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
                   'Kenneth', 'Carol', 'Kevin', 'Amanda', 'Brian', 'Dorothy', 'George', 'Melissa', 'Timothy', 'Deborah']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
                  'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
                  'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
                  'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
                  'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter', 'Roberts']
    
    people = []
    for i in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        height = round(random.uniform(140, 200), 2)  # in cm
        weight = round(random.uniform(40, 120), 2)   # in kg
        people.append([name, age, height, weight])
    
    # Write CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(people)
        # Calculate averages
        ages = [p[1] for p in people]
        heights = [p[2] for p in people]
        weights = [p[3] for p in people]
        avg_age = round(mean(ages), 2)
        avg_height = round(mean(heights), 2)
        avg_weight = round(mean(weights), 2)
        writer.writerow(['Average', avg_age, avg_height, avg_weight])
    
    return filename
