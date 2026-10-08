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
        
    sampled_tasks = random.choices(task_list, k=n_tasks)
    sampled_tasks_sanitized = [t.replace(' ', '_') for t in sampled_tasks]
    assigned_employees = random.choices(employees, k=n_tasks)
    due_date = datetime.now().date()
    
    df = pd.DataFrame({
        'Task Name': sampled_tasks_sanitized,
        'Assigned To': assigned_employees,
        'Due Date': [due_date] * n_tasks
    })
    return df