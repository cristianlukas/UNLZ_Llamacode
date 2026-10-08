import pandas as pd
from datetime import datetime
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    # Input validity check
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a number")
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
        
    random.seed(random_seed)
    
    start_date = datetime.fromtimestamp(epoch_milliseconds / 1000)
    end_date = datetime.now()
    
    # Generate dates
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    data = []
    for date in dates:
        for product in products:
            sales = random.randint(10, 50)
            data.append({'Product': product, 'Date': date, 'Sales': sales})
            
    return pd.DataFrame(data)