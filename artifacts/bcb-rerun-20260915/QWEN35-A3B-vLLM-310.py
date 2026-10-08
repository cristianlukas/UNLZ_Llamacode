import os
import csv
import random
from statistics import mean

COLUMNS = ['Name', 'Age', 'Height', 'Weight']
PEOPLE_COUNT = 100

def task_func(filename):
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    data = []
    ages = []
    heights = []
    weights = []
    
    for i in range(PEOPLE_COUNT):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        height = round(random.uniform(150, 200), 2)
        weight = round(random.uniform(40, 120), 2)
        
        data.append([name, age, height, weight])
        ages.append(age)
        heights.append(height)
        weights.append(weight)
        
    avg_age = mean(ages)
    avg_height = mean(heights)
    avg_weight = mean(weights)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(data)
        writer.writerow(['Average', avg_age, avg_height, avg_weight])
        
    return filename