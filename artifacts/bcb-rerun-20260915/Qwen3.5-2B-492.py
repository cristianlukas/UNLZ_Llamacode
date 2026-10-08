import pandas as pd
from datetime import datetime, timedelta
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    # Validate input
    if epoch_milliseconds < 0:
        raise ValueError("Epoch time must be non-negative.")
    
    # Set random seed for reproducibility
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    current_time = datetime.utcfromtimestamp(epoch_milliseconds / 1000.0)
    
    # Calculate the number of days to generate
    days_to_generate = (current_time - current_time).days
    
    if days_to_generate <= 0:
        # If current time is before or equal to epoch, generate 0 days
        days_to_generate = 0
    
    # Generate random sales data
    sales_data = []
    
    for day in range(days_to_generate + 1):
        date = current_time - timedelta(days=day)
        
        for product in products:
            # Generate random sales quantity between 10 and 50
            sales = random.randint(10, 50)
            sales_data.append({
                'Product': product,
                'Date': date,
                'Sales': sales
            })
    
    # Create DataFrame
    df = pd.DataFrame(sales_data)
    
    return df