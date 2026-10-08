import pandas as pd
from datetime import datetime, timedelta
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be an integer or float representing milliseconds since epoch.")
    
    random.seed(random_seed)
    
    start_time = datetime.fromtimestamp(epoch_milliseconds / 1000)
    current_time = datetime.now()
    
    if start_time > current_time:
        raise ValueError("Start time cannot be in the future.")
    
    sales_data = []
    
    current_date = start_time.date()
    end_date = current_time.date()
    
    while current_date <= end_date:
        for product in products:
            sales = random.randint(10, 50)
            sales_data.append({
                'Product': product,
                'Date': current_date,
                'Sales': sales
            })
        current_date += timedelta(days=1)
    
    df = pd.DataFrame(sales_data)
    df['Date'] = pd.to_datetime(df['Date'])
    
    return df