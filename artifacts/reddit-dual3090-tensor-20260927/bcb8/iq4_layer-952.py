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
    # However, to be safe, we handle the case where n_tasks > len(task_list) by using all available tasks
    # Actually, let's re-read: "Randomly assigns a specified number of tasks" - this implies we pick n_tasks from task_list
    # If n_tasks > len(task_list), random.sample will raise an error. Let's handle this by using replacement or capping.
    # The problem doesn't specify, but typically we'd cap at len(task_list). Let's use min(n_tasks, len(task_list))
    
    # Re-do: select min(n_tasks, len(sanitized_tasks)) tasks
    num_to_select = min(n_tasks, len(sanitized_tasks))
    selected_tasks = random.sample(sanitized_tasks, num_to_select)
    
    # Assign each selected task to a random employee
    assignments = []
    for task in selected_tasks:
        employee = random.choice(employees)
        due_date = datetime.now().strftime('%Y-%m-%d')
        assignments.append({
            'Task Name': task,
            'Assigned To': employee,
            'Due Date': due_date
        })
    
    return pd.DataFrame(assignments, columns=['Task Name', 'Assigned To', 'Due Date'])
