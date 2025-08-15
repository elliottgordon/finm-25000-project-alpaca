# Import api connection details.


import os
import sys

# Add parent directory (project root) to Python path so Alpaca_API.py can be imported
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


from Alpaca_API import ALPACA_KEY, ALPACA_SECRET

# Import alpaca trade api.
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.data.historical import StockHistoricalDataClient

client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

# Define the function to get historical data
def get_last_quote():
    symbols = ["SPY", "VXX"]

    request_params = StockLatestQuoteRequest(symbol_or_symbols=symbols)
    latest_quote = client.get_stock_latest_quote(request_params)
    print(latest_quote)
    return latest_quote

get_last_quote()

# 1. Getting historical data from alpaca
# 2. Updating that historical from with some frequency
# 3. Saving/making the historical data easily available for backtesting
# 4. Cleaning, etc.

# Extract -> Transform -> Load (ETL)
# Extracting data from somewhere
# Transforming the data to make it look like what you want
# Loading the data into a database/"data lake" <- clean "pool" of data

# when filling trades and managing your positions, want to use real time data because you want to cross the bid asks to implement trading costs (also more realistic trades because you need to know the proper liquidity)