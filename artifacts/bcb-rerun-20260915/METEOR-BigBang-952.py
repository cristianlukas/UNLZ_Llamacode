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
        raise ValueError("n_tasks must not be negative.")
    
    if seed is not None:
        random.seed(seed)
    
    sanitized_tasks = [t.replace(" ", "_") for t in task_list]
    
    selected_tasks = random.sample(sanitized_tasks, n_tasks) if n_tasks <= len(sanitized_tasks) else random.choices(sanitized_tasks, k=n_tasks)
    
    assigned_employees = [random.choice(employees) for _ in selected_tasks]
    
    due_date = datetime.now().date()
    
    df = pd.DataFrame({
        "Task Name": selected_tasks,
        "Assigned To": assigned_employees,
        "Due Date": [due_date] * len(selected_tasks),
    })
    
    return df