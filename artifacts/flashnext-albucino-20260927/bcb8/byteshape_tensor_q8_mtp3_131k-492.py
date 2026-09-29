import pandas as pd
from datetime import datetime
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    # Check input validity
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a numeric value")
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
    
    # Set random seed
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    start_datetime = datetime.fromtimestamp(epoch_milliseconds / 1000.0)
    current_datetime = datetime.now()
    
    # Ensure start is not after current
    if start_datetime > current_datetime:
        raise ValueError("epoch_milliseconds represents a future time")
    
    # Generate dates from start date to current date (inclusive)
    start_date = start_datetime.date()
    end_date = current_datetime.date()
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date = datetime.combine(current_date, datetime.min.time()).replace(day=current_date.day + 1).date() if current_date.day < 28 else None
        if current_date is None:
            break
    
    # More robust date generation
    dates = []
    current_date = start_date
    from datetime import timedelta
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Generate sales data
    records = []
    for date in dates:
        for product in products:
            sales = random.randint(10, 50)
            records.append({
                'Product': product,
                'Date': datetime.combine(date, datetime.min.time()),
                'Sales': sales
            })
    
    df = pd.DataFrame(records, columns=['Product', 'Date', 'Sales'])
    return df
