import pandas as pd
import random
from datetime import datetime

def task_func(
    task_list,
    n_tasks,
    employees=["John Doe", "Jane Smith", "James Brown", "Mary Johnson", "Robert Davis"],
    seed=None,
):
    if n_tasks < 0:
        raise ValueError("n_tasks must be non-negative")
    
    if seed is not None:
        random.seed(seed)
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    if n_tasks > len(task_list):
        n_tasks = len(task_list)
    
    selected_tasks = random.sample(task_list, n_tasks)
    sanitized_tasks = [task.replace(" ", "_") for task in selected_tasks]
    
    assignments = []
    for i in range(n_tasks):
        assignments.append({
            'Task Name': sanitized_tasks[i],
            'Assigned To': employees[i % len(employees)],
            'Due Date': current_date
        })
    
    return pd.DataFrame(assignments)