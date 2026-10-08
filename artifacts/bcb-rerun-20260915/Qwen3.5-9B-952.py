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
        raise ValueError("n_tasks cannot be negative")
    
    if seed is not None:
        random.seed(seed)
    
    # Sanitize task names by replacing spaces with underscores
    sanitized_tasks = [task.replace(" ", "_") for task in task_list]
    
    # Set due date to current system date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Randomly assign tasks to employees
    assignments = []
    for _ in range(n_tasks):
        task_name = random.choice(sanitized_tasks)
        assigned_to = random.choice(employees)
        assignments.append({
            "Task Name": task_name,
            "Assigned To": assigned_to,
            "Due Date": today
        })
    
    return pd.DataFrame(assignments)