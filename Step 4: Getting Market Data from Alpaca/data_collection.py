# Basic data collection for Step 4

import os
from datetime import datetime, timedelta
import pandas as pd
import pytz
import sqlalchemy
from step4_api import get_daily_bars

def insert_data_frame(data, engine):
    # Save the data to the database
    if not data.empty:
        data.to_sql('market_data', engine, if_exists='append', index=False)

def get_latest_timestamp(engine):
    try:
        query = "SELECT MAX(timestamp) FROM market_data"
        result = pd.read_sql(query, engine)
        return result.iloc[0, 0]
    except:
        return None

def run_data_saver(symbols: list):
    eastern = pytz.timezone('US/Eastern')
    # Use 7 years of historical data
    start = eastern.localize(datetime(2018, 1, 1))
    end = eastern.localize(datetime.now() - timedelta(days=1))

    # Database path points to Step 5 folder
    db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
    engine = sqlalchemy.create_engine(f'sqlite:///{os.path.abspath(db_path)}')
    
    latest_timestamp = get_latest_timestamp(engine)
    
    if latest_timestamp:
        # Update existing data
        try:
            # Simple string parsing for the timestamp
            if latest_timestamp:
                timestamp_str = str(latest_timestamp)[:10]  # Get YYYY-MM-DD part
                latest_dt = eastern.localize(datetime.strptime(timestamp_str, "%Y-%m-%d"))
            else:
                latest_dt = start
        except:
            latest_dt = start
            
        if datetime.now().weekday() < 5:  # Weekday check
            new_start = latest_dt + timedelta(days=1)
            new_end = end
            if new_start < new_end:
                new_data = get_daily_bars(symbols, new_start, new_end)
                insert_data_frame(new_data, engine)
                print(f"Added {len(new_data)} new records")
    else:
        # Initial data load
        data = get_daily_bars(symbols, start, end)
        insert_data_frame(data, engine)
        print(f"Initial load: {len(data)} records")

if __name__ == "__main__":
    # Load symbols same way as scheduler
    def _load_watchlist():
        env_syms = os.getenv("ALPACA_SYMBOLS")
        if env_syms:
            return [s.strip().upper() for s in env_syms.split(",") if s.strip()]
        wl_path = os.path.join(os.path.dirname(__file__), "watchlist.txt")
        if os.path.exists(wl_path):
            out = []
            with open(wl_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        out.append(line.upper())
            if out:
                return out
        return ["SPY", "VXX"]
    run_data_saver(_load_watchlist())