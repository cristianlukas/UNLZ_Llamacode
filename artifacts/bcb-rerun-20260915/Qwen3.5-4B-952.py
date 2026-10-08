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
    
    assigned_tasks = []
    for i in range(n_tasks):
        if i < len(task_list):
            task_name = task_list[i].replace(" ", "_")
        else:
            task_name = f"Task_{i+1}".replace(" ", "_")
        
        assigned_employee = random.choice(employees)
        
        assigned_tasks.append({
            "Task Name": task_name,
            "Assigned To": assigned_employee,
            "Due Date": current_date
        })
    
    return pd.DataFrame(assigned_tasks)