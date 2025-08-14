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
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.data.enums import Adjustment
from alpaca.data.timeframe import TimeFrame

import sqlalchemy
import pandas as pd
import pytz
from datetime import datetime, timedelta


client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

def get_historical_data(symbols, start, end):
    # Gets historical data from Alpaca
    request_params = StockBarsRequest(
                        symbol_or_symbols=symbols,
                        timeframe=TimeFrame.Day,  # Changed from Minute to Day for paper trading
                        start=start,
                        end=end,
                        adjustment=Adjustment.ALL) # adjust for dividends and stock splits
    bars = client.get_stock_bars(request_params).df.reset_index()
    return bars

def get_latest_quote(symbols):
    request_params = StockLatestQuoteRequest(symbol_or_symbols=symbols)
    latest_quote = client.get_stock_latest_quote(request_params)
    return latest_quote

def insert_data_frame(data, engine):
    # Save the data to my database
    data.to_sql('market_data', engine, if_exists='append', index=False)

def get_latest_timestamp(engine):
    query = "SELECT MAX(timestamp) FROM market_data"
    result = pd.read_sql(query, engine)
    return result.iloc[0, 0]

def run_data_saver():
    # DO NOT HARD CODE THE FOLLOWING THREE VARIABLES
    eastern = pytz.timezone('US/Eastern')
    # Modified for paper trading account limitations - use recent data only
    # Use 7 years of historical data - maximum available with Alpaca Basic plan (free IEX data)
    # Based on testing: can collect ~3,500+ records with 7-year daily data
    start = eastern.localize(datetime(2018, 1, 1))  # Start from Jan 1, 2018 (7 years back)
    end = eastern.localize(datetime.now() - timedelta(days=1))  # End yesterday (avoid recent data issues)
    symbols = ["SPY", "VXX"]

    engine = sqlalchemy.create_engine('sqlite:///market_data.db')
    
    try:
        latest_timestamp = get_latest_timestamp(engine)
    except sqlalchemy.exc.OperationalError:
        latest_timestamp = None
    
    if latest_timestamp:
        latest_timestamp = datetime.strptime(latest_timestamp, "%Y-%m-%d %H:%M:%S.%f").astimezone(pytz.timezone('US/Eastern'))
        
        eastern = pytz.timezone('US/Eastern')
        one_minute_ago = eastern.localize(datetime.now()) - timedelta(minutes=1)

        # Check that today isn't a weekend
        if datetime.now().weekday() < 5 and latest_timestamp > one_minute_ago:
            # Get historical data
            new_start = latest_timestamp + timedelta(seconds=1)
            new_end = eastern.localize(datetime.now())  # Make timezone-aware
            new_data = get_historical_data(symbols, new_start, new_end)
            insert_data_frame(new_data, engine)

    else:
        # Get historical data for the initial date range
        data = get_historical_data(symbols, start, end)
        insert_data_frame(data, engine)
        
run_data_saver()