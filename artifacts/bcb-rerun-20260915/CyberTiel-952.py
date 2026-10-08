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
    n_tasks (int): The number of tasks to be assigned.
    employees (list): A list of employee names from whom tasks can be assigned.
    seed (int): The random seed for reproducibility.

    Returns:
    pd.DataFrame: A DataFrame containing the assigned tasks with columns 'Task Name', 'Assigned To', and 'Due Date'.

    Raises:
    ValueError: If n_tasks is negative.
    """
    if n_tasks < 0:
        raise ValueError("n_tasks must be non-negative.")

    if seed is not None:
        random.seed(seed)

    # Sanitize task names by replacing spaces with underscores
    sanitized_tasks = [task.replace(" ", "_") for task in task_list]

    # Randomly select tasks to assign
    selected_tasks = random.sample(sanitized_tasks, n_tasks)

    # Randomly assign each selected task to an employee
    assigned_employees = [random.choice(employees) for _ in selected_tasks]

    # Set the due date to the current system date
    current_date = datetime.now().date()
    due_dates = [current_date for _ in selected_tasks]

    # Create a DataFrame with the assignments
    assignments_df = pd.DataFrame(
        {
            "Task Name": selected_tasks,
            "Assigned To": assigned_employees,
            "Due Date": due_dates,
        }
    )

    return assignments_df