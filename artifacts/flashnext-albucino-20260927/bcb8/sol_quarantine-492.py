```python
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
        raise ValueError("epoch_milliseconds must be a numeric type")
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
    
    # Set random seed
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    start_dt = datetime.fromtimestamp(epoch_milliseconds / 1000)
    end_dt = datetime.now()
    
    # Generate all dates from start to end (inclusive)
    dates = []
    current = start_dt
    while current <= end_dt:
        dates.append(current)
        current = current.replace(hour=0, minute=0, second=0, microsecond=0)
        current = current + pd.Timedelta(days=1)
    
    # If start date is after end date, return empty DataFrame
    if not dates:
        return pd.DataFrame(columns=['Product', 'Date', 'Sales'])
    
    # Generate sales data
    data = []
    for date in dates:
        for product in products:
            sales = random.randint(10, 50)
            data.append({
                'Product': product,
                'Date': date,
                'Sales': sales
            })
    
    df = pd.DataFrame(data, columns=['Product', 'Date', 'Sales'])
    return df