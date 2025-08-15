"""Simple sample to fetch daily bars and print them."""

from datetime import datetime, timedelta
import pytz
from step4_api import get_daily_bars

# Get last 30 days of data
eastern = pytz.timezone("US/Eastern")
end = eastern.localize(datetime.now() - timedelta(days=1))
start = eastern.localize(datetime.now() - timedelta(days=30))

symbols = ["SPY", "VXX"]

df = get_daily_bars(symbols, start, end)
print("Sample data:")
print(df.head())
print(f"Total rows: {len(df)}, Symbols: {df['symbol'].unique().tolist()}")
