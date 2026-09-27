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
    
    if n_tasks == 0:
        return pd.DataFrame(columns=['Task Name', 'Assigned To', 'Due Date'])
    
    # Sanitize task names by replacing spaces with underscores
    sanitized_tasks = [task.replace(' ', '_') for task in task_list]
    
    # Randomly select n_tasks from the sanitized task list
    selected_tasks = random.sample(sanitized_tasks, n_tasks)
    
    # Randomly assign employees
    assigned_employees = [random.choice(employees) for _ in range(n_tasks)]
    
    # Set due dates to current system date
    current_date = datetime.now().date()
    due_dates = [current_date] * n_tasks
    
    # Create DataFrame
    df = pd.DataFrame({
        'Task Name': selected_tasks,
        'Assigned To': assigned_employees,
        'Due Date': due_dates
    })
    
    return df
