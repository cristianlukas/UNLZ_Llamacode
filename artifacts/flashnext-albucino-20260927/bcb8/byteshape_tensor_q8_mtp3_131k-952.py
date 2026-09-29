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
    selected_tasks = random.sample(sanitized_tasks, min(n_tasks, len(sanitized_tasks)))
    
    # If n_tasks is greater than the number of available tasks, we can't assign more than available
    # But the problem says "randomly assigns a specified number of tasks", so we assume n_tasks <= len(task_list)
    # However, to be safe, if n_tasks > len(task_list), we use all tasks
    if n_tasks > len(sanitized_tasks):
        selected_tasks = sanitized_tasks[:]
        random.shuffle(selected_tasks)
    
    # Assign each task to a random employee
    assigned_employees = [random.choice(employees) for _ in selected_tasks]
    
    # Set due date to current system date
    current_date = datetime.now().date()
    due_dates = [current_date] * len(selected_tasks)
    
    # Create DataFrame
    df = pd.DataFrame({
        'Task Name': selected_tasks,
        'Assigned To': assigned_employees,
        'Due Date': due_dates
    })
    
    return df
