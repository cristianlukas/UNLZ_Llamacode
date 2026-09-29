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
    
    current_date = datetime.now().date()
    
    # Sanitize task names by replacing spaces with underscores
    sanitized_tasks = [task.replace(" ", "_") for task in task_list]
    
    # Randomly assign tasks
    assignments = []
    for _ in range(n_tasks):
        task = random.choice(sanitized_tasks)
        employee = random.choice(employees)
        assignments.append({
            "Task Name": task,
            "Assigned To": employee,
            "Due Date": current_date
        })
    
    df = pd.DataFrame(assignments, columns=["Task Name", "Assigned To", "Due Date"])
    return df
