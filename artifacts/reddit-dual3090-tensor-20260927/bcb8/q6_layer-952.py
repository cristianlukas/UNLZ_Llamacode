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
    
    # Sanitize task names by replacing spaces with underscores
    sanitized_tasks = [task.replace(" ", "_") for task in task_list]
    
    # Randomly select n_tasks from the sanitized task list
    if n_tasks == 0:
        return pd.DataFrame(columns=['Task Name', 'Assigned To', 'Due Date'])
    
    # If n_tasks is greater than the number of available tasks, we can still assign
    # but we need to handle the case where we might not have enough tasks.
    # The problem says "randomly assigns a specified number of tasks", so we assume
    # n_tasks <= len(task_list) or we can sample with replacement? Let's assume without replacement
    # but if n_tasks > len(task_list), we'll just use all available tasks? 
    # Actually, let's just sample n_tasks from the list. If n_tasks > len(task_list), 
    # we might need to handle that. Let's assume n_tasks <= len(task_list) for simplicity,
    # but to be safe, let's sample with replacement if needed? No, let's just sample without replacement
    # and if n_tasks > len(task_list), we'll raise an error or just use all? 
    # The problem doesn't specify, so let's just sample n_tasks from the list.
    # If n_tasks > len(task_list), random.sample will raise an error. Let's handle that.
    
    if n_tasks > len(sanitized_tasks):
        # If we need more tasks than available, we can either raise an error or sample with replacement
        # Let's sample with replacement to ensure we can always assign n_tasks
        selected_tasks = [random.choice(sanitized_tasks) for _ in range(n_tasks)]
    else:
        selected_tasks = random.sample(sanitized_tasks, n_tasks)
    
    # Randomly assign each task to an employee
    assigned_employees = [random.choice(employees) for _ in range(n_tasks)]
    
    # Create the DataFrame
    df = pd.DataFrame({
        'Task Name': selected_tasks,
        'Assigned To': assigned_employees,
        'Due Date': [current_date] * n_tasks
    })
    
    return df
