import pandas as pd
from datetime import datetime
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a number")
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
    
    random.seed(random_seed)
    
    start_dt = datetime.fromtimestamp(epoch_milliseconds / 1000.0)
    current_dt = datetime.now()
    
    # Ensure start_dt is not in the future
    if start_dt > current_dt:
        raise ValueError("epoch_milliseconds represents a future date")
    
    # Generate all dates from start_dt to current_dt (inclusive)
    dates = []
    current_date = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    while current_date <= end_date:
        dates.append(current_date)
        current_date = (current_date + pd.Timedelta(days=1))
    
    # Generate sales data
    records = []
    for date in dates:
        for product in products:
            sales = random.randint(10, 50)
            records.append({
                'Product': product,
                'Date': date,
                'Sales': sales
            })
    
    df = pd.DataFrame(records, columns=['Product', 'Date', 'Sales'])
    return df
