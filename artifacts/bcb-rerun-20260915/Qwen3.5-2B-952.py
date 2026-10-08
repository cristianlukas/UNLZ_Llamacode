import pandas as pd
import random
from datetime import datetime

def task_func(
    task_list,
    n_tasks,
    employees=["John Doe", "Jane Smith", "James Brown", "Mary Johnson", "Robert Davis"],
    seed=None,
):
    # Validate input
    if n_tasks < 0:
        raise ValueError("n_tasks cannot be negative")
    
    # Sanitize task names by replacing spaces with underscores
    sanitized_task_list = [task.replace(" ", "_") for task in task_list]
    
    # Set seed for reproducibility if provided
    if seed is not None:
        random.seed(seed)
    
    # Assign tasks to employees
    assignments = []
    for i in range(n_tasks):
        task_name = sanitized_task_list[i]
        employee = employees[i % len(employees)]
        due_date = datetime.now().date()
        assignments.append({
            'Task Name': task_name,
            'Assigned To': employee,
            'Due Date': due_date
        })
    
    # Create DataFrame
    df = pd.DataFrame(assignments)
    
    return df