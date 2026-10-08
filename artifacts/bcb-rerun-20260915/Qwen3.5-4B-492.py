import pandas as pd
from datetime import datetime, timedelta
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a numeric value representing milliseconds since epoch.")
    
    random.seed(random_seed)
    
    start_time = datetime.fromtimestamp(epoch_milliseconds / 1000)
    current_time = datetime.now()
    
    if start_time > current_time:
        raise ValueError("Start time cannot be after current time.")
    
    if start_time.tzinfo is not None and current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=start_time.tzinfo)
    elif start_time.tzinfo is None and current_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=current_time.tzinfo)
    
    date_range = pd.date_range(start=start_time, end=current_time, freq='D')
    
    data = []
    for date in date_range:
        for product in products:
            sales = random.randint(10, 50)
            data.append({
                'Product': product,
                'Date': date,
                'Sales': sales
            })
    
    df = pd.DataFrame(data)
    return df