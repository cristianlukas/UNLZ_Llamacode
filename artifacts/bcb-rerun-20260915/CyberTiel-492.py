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
    epoch_milliseconds (int): The starting time in epoch milliseconds.
    random_seed (int): The seed for random number generation (default is 0).
    products (list): A list of product names (default is five products).

    Returns:
    pd.DataFrame: A DataFrame containing sales data with columns 'Product', 'Date', and 'Sales'.
    """
    # Check input validity
    if not isinstance(epoch_milliseconds, int):
        raise ValueError("epoch_milliseconds must be an integer.")
    if len(products) != 5:
        raise ValueError("There must be exactly five products.")

    # Set the random seed
    random.seed(random_seed)

    # Convert epoch milliseconds to datetime
    start_date = datetime.fromtimestamp(epoch_milliseconds / 1000)
    end_date = datetime.now()

    # Generate a range of dates from start_date to end_date
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # Generate sales data
    data = []
    for date in date_range:
        for product in products:
            sales = random.randint(10, 50)
            data.append({"Product": product, "Date": date, "Sales": sales})

    # Create a DataFrame
    df = pd.DataFrame(data)

    return df