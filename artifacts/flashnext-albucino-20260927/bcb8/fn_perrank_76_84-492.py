import pandas as pd
from datetime import datetime
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    # Validate input
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a number")
    
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
    
    # Set random seed for reproducibility
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    start_date = datetime.utcfromtimestamp(epoch_milliseconds / 1000.0)
    end_date = datetime.utcnow()
    
    # Get the date parts (ignore time)
    start_day = start_date.date()
    end_day = end_date.date()
    
    # Generate all dates between start_day and end_day inclusive
    from datetime import timedelta
    dates = []
    current = start_day
    while current <= end_day:
        dates.append(current)
        current += timedelta(days=1)
    
    # Generate sales data
    records = []
    for date in dates:
        for product in products:
            sales = random.randint(10, 50)
            records.append({
                'Product': product,
                'Date': datetime(date.year, date.month, date.day),
                'Sales': sales
            })
    
    df = pd.DataFrame(records, columns=['Product', 'Date', 'Sales'])
    return df
