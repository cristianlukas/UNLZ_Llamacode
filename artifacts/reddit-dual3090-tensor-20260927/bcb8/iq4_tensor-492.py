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
    start_dt = datetime.fromtimestamp(epoch_milliseconds / 1000.0)
    current_dt = datetime.now()
    
    # Get the date part (midnight) for start and current
    start_date = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    current_date = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Generate list of dates from start_date to current_date (inclusive)
    dates = []
    current = start_date
    while current <= current_date:
        dates.append(current)
        current = current.replace(day=current.day + 1) if current.day < 28 else None
        if current is None:
            # Handle month/year rollover
            from datetime import timedelta
            current = start_date
            # Use timedelta for proper date increment
            break
    
    # Better approach using timedelta
    from datetime import timedelta
    dates = []
    current = start_date
    while current <= current_date:
        dates.append(current)
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
