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
        raise ValueError("epoch_milliseconds must be a numeric value")
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
    
    # Set random seed
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    start_dt = datetime.fromtimestamp(epoch_milliseconds / 1000.0)
    current_dt = datetime.now()
    
    # Get start and end dates (date only)
    start_date = start_dt.date()
    end_date = current_dt.date()
    
    # Generate list of dates from start_date to end_date inclusive
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(datetime.combine(current, datetime.min.time()))
        current = current.replace(day=current.day + 1) if current.day < 28 else None
        if current is None:
            # Handle month/year rollover
            if current_dt.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)
    
    # Actually, let's use a simpler approach with timedelta
    from datetime import timedelta
    
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(datetime.combine(current, datetime.min.time()))
        current = current + timedelta(days=1)
    
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
