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
    if not isinstance(products, list) or len(products) != 5:
        raise ValueError("products must be a list of exactly 5 product names")
    for p in products:
        if not isinstance(p, str):
            raise ValueError("all product names must be strings")

    random.seed(random_seed)

    start_date = datetime.fromtimestamp(epoch_milliseconds / 1000.0)
    current_date = datetime.now()

    # Generate all dates from start date to current date (inclusive)
    num_days = (current_date.date() - start_date.date()).days + 1
    if num_days < 1:
        num_days = 1

    date_range = [start_date.date() + pd.Timedelta(days=i) for i in range(num_days)]

    records = []
    for d in date_range:
        for product in products:
            sales = random.randint(10, 50)
            records.append({
                'Product': product,
                'Date': d,
                'Sales': sales
            })

    df = pd.DataFrame(records)
    return df