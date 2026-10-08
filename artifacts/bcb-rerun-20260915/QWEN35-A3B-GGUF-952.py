import pandas as pd
import random
from datetime import datetime

def task_func(
    task_list,
    n_tasks,
    employees=["John Doe", "Jane Smith", "James Brown", "Mary Johnson", "Robert Davis"],
    seed=None,
):
    """
    Randomly assigns a specified number of tasks to employees with a due date of the current day.
    
    Parameters:
    task_list (list): A list of task names to be assigned.
    n_tasks (int): The number of tasks to assign.
    employees (list): A list of employee names to assign tasks to.
    seed (int, optional): A seed for the random number generator for reproducibility.
    
    Returns:
    pd.DataFrame: A DataFrame containing the assigned tasks with columns 'Task Name', 'Assigned To', and 'Due Date'.
    
    Raises:
    ValueError: If n_tasks is negative.
    """
    if n_tasks < 0:
        raise ValueError("n_tasks cannot be negative.")
    
    if seed is not None:
        random.seed(seed)
    
    # Sanitize task names by replacing spaces with underscores
    sanitized_tasks = [task.replace(" ", "_") for task in task_list]
    
    # Get the current system date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Randomly select n_tasks from the sanitized task list
    selected_tasks = random.sample(sanitized_tasks, min(n_tasks, len(sanitized_tasks)))
    
    # Randomly assign each selected task to an employee
    assignments = []
    for task in selected_tasks:
        assigned_employee = random.choice(employees)
        assignments.append({
            "Task Name": task,
            "Assigned To": assigned_employee,
            "Due Date": current_date
        })
    
    # Create a DataFrame from the assignments
    df_assignments = pd.DataFrame(assignments)
    
    return df_assignments