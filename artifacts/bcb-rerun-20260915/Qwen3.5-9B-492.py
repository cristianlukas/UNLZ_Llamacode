import pandas as pd
from datetime import datetime
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    # Validate input type
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a number")
    
    # Validate products list
    if not isinstance(products, list):
        raise ValueError("products must be a list")
    if len(products) == 0:
        raise ValueError("products list cannot be empty")
    
    # Set random seed
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    start_time = datetime.utcfromtimestamp(epoch_milliseconds / 1000.0)
    
    # Get current time
    end_time = datetime.utcnow()
    
    # Validate time range
    if start_time > end_time:
        raise ValueError("Epoch time is in the future")
    
    # Generate dates from start to end (inclusive)
    current_date = start_time
    dates = []
    while current_date <= end_time:
        dates.append(current_date)
        current_date += pd.Timedelta(days=1)
    
    # Generate sales data
    data = []
    for product in products:
        for date in dates:
            sales = random.randint(10, 50)
            data.append({
                'Product': product,
                'Date': date,
                'Sales': sales
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    return df