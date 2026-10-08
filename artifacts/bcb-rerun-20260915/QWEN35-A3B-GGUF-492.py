import pandas as pd
from datetime import datetime
import random

def task_func(
    epoch_milliseconds,
    random_seed=0,
    products=["Product1", "Product2", "Product3", "Product4", "Product5"],
):
    """
    Generate sales data for five products from a given epoch time up to the current time.
    
    Parameters:
    epoch_milliseconds (int): The epoch time in milliseconds to start generating sales data from.
    random_seed (int): The random seed for reproducibility.
    products (list): A list of product names.
    
    Returns:
    pd.DataFrame: A DataFrame containing sales data with columns 'Product', 'Date', and 'Sales'.
    """
    # Check input validity
    if not isinstance(epoch_milliseconds, (int, float)):
        raise ValueError("epoch_milliseconds must be a number")
    if epoch_milliseconds < 0:
        raise ValueError("epoch_milliseconds must be non-negative")
    if not isinstance(random_seed, int):
        raise ValueError("random_seed must be an integer")
    if not isinstance(products, list) or len(products) != 5:
        raise ValueError("products must be a list of 5 product names")
    
    # Set the random seed
    random.seed(random_seed)
    
    # Convert epoch milliseconds to datetime
    start_date = datetime.fromtimestamp(epoch_milliseconds / 1000)
    current_date = datetime.now()
    
    # Generate sales data
    sales_data = []
    for date in pd.date_range(start=start_date, end=current_date, freq='D'):
        for product in products:
            sales = random.randint(10, 50)
            sales_data.append({'Product': product, 'Date': date, 'Sales': sales})
    
    # Create DataFrame
    df = pd.DataFrame(sales_data)
    
    return df