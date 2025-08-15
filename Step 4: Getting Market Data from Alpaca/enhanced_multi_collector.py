# Enhanced Multi-Asset Data Collector
# Based on your working data_saver.py, expanded for multiple assets

import os
import sys

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from Alpaca_API import ALPACA_KEY, ALPACA_SECRET
from asset_universe import get_priority_universe, get_etf_universe

# Import alpaca API (using your working imports)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.enums import Adjustment
from alpaca.data.timeframe import TimeFrame

import sqlalchemy
import pandas as pd
import pytz
from datetime import datetime, timedelta
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_multi_collector.log'),
        logging.StreamHandler()
    ]
)

client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

def get_historical_data(symbols, start, end):
    """Get historical data from Alpaca - enhanced from your working version"""
    all_data = []
    
    for symbol in symbols:
        try:
            logging.info(f"Requesting data for {symbol}")
            
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],  # Single symbol as list
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                adjustment=Adjustment.ALL
            )
            
            bars = client.get_stock_bars(request_params).df.reset_index()
            
            if not bars.empty:
                all_data.append(bars)
                logging.info(f"✅ {symbol}: {len(bars)} records")
            else:
                logging.warning(f"⚠️ {symbol}: No data")
            
            # Small delay to be respectful
            time.sleep(0.2)
            
        except Exception as e:
            logging.error(f"❌ {symbol}: {str(e)}")
            continue
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        logging.info(f"Total records retrieved: {len(combined)}")
        return combined
    else:
        return pd.DataFrame()

def insert_data_frame(data, engine):
    """Save data to database - your working version"""
    data.to_sql('market_data', engine, if_exists='append', index=False)

def get_latest_timestamp(engine, symbol=None):
    """Get latest timestamp - enhanced version"""
    try:
        if symbol:
            query = "SELECT MAX(timestamp) FROM market_data WHERE symbol = ?"
            result = pd.read_sql(query, engine, params=[symbol])
        else:
            query = "SELECT MAX(timestamp) FROM market_data"
            result = pd.read_sql(query, engine)
        return result.iloc[0, 0]
    except:
        return None

def get_existing_symbols(engine):
    """Get symbols already in database"""
    try:
        query = "SELECT DISTINCT symbol FROM market_data"
        result = pd.read_sql(query, engine)
        return result['symbol'].tolist()
    except:
        return []

def run_enhanced_data_saver(symbol_list=None, lookback_years=2):
    """Enhanced version of your run_data_saver function"""
    
    if symbol_list is None:
        # Start with conservative ETF list
        priority_universe = get_priority_universe()
        symbol_list = priority_universe['tier_1_etfs'][:10]  # First 10 ETFs
    
    logging.info(f"Starting collection for symbols: {symbol_list}")
    
    # Date range setup (your working version)
    eastern = pytz.timezone('US/Eastern')
    start = eastern.localize(datetime(datetime.now().year - lookback_years, 1, 1))
    end = eastern.localize(datetime.now() - timedelta(days=1))
    
    # Database setup (your working version)
    db_path = '../Step 5: Saving Market Data/market_data.db'
    engine = sqlalchemy.create_engine(f'sqlite:///{db_path}')
    
    # Check existing data
    existing_symbols = get_existing_symbols(engine)
    logging.info(f"Existing symbols in database: {len(existing_symbols)}")
    
    # Process symbols in smaller batches
    batch_size = 3  # Small batches to avoid rate limits
    total_records = 0
    
    for i in range(0, len(symbol_list), batch_size):
        batch = symbol_list[i:i+batch_size]
        logging.info(f"Processing batch {i//batch_size + 1}: {batch}")
        
        try:
            # Check if symbols need updates
            symbols_to_collect = []
            for symbol in batch:
                latest_timestamp = get_latest_timestamp(engine, symbol)
                if latest_timestamp is None:
                    symbols_to_collect.append(symbol)
                    logging.info(f"{symbol}: New symbol, collecting full history")
                elif latest_timestamp:
                    # Parse the timestamp and check if it's recent
                    try:
                        if isinstance(latest_timestamp, str):
                            latest_date = datetime.strptime(latest_timestamp.split()[0], "%Y-%m-%d").date()
                        else:
                            latest_date = latest_timestamp.date()
                        
                        days_old = (datetime.now().date() - latest_date).days
                        
                        if days_old > 7:  # More than a week old
                            symbols_to_collect.append(symbol)
                            logging.info(f"{symbol}: Data is {days_old} days old, updating")
                        else:
                            logging.info(f"{symbol}: Up to date ({days_old} days old)")
                    except:
                        symbols_to_collect.append(symbol)
                        logging.info(f"{symbol}: Could not parse timestamp, collecting")
            
            if symbols_to_collect:
                # Get historical data for symbols that need updating
                data = get_historical_data(symbols_to_collect, start, end)
                
                if not data.empty:
                    insert_data_frame(data, engine)
                    batch_records = len(data)
                    total_records += batch_records
                    logging.info(f"✅ Batch inserted: {batch_records} records")
                else:
                    logging.warning(f"⚠️ No data retrieved for batch: {batch}")
            
            # Delay between batches
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"❌ Batch failed: {str(e)}")
            continue
    
    # Final summary
    final_symbols = get_existing_symbols(engine)
    logging.info(f"🎉 Collection complete!")
    logging.info(f"   Total symbols in database: {len(final_symbols)}")
    logging.info(f"   Records added this session: {total_records}")
    
    return {
        'symbols_in_db': len(final_symbols),
        'records_added': total_records,
        'symbol_list': final_symbols
    }

def main():
    """Main function for enhanced collection"""
    print("🚀 Enhanced Multi-Asset Data Collection")
    print("=" * 60)
    
    # Show available universe
    priority_universe = get_priority_universe()
    print("\n📊 Available Asset Tiers:")
    for tier, symbols in priority_universe.items():
        print(f"   {tier}: {len(symbols)} symbols")
    
    # Start with Tier 1 ETFs (most reliable)
    tier_1_symbols = priority_universe['tier_1_etfs']
    print(f"\n🎯 Starting with Tier 1 ETFs:")
    print(f"   Symbols: {tier_1_symbols}")
    
    # Run collection
    result = run_enhanced_data_saver(tier_1_symbols, lookback_years=2)
    
    print(f"\n📈 Final Results:")
    print(f"   Total symbols in database: {result['symbols_in_db']}")
    print(f"   Records added: {result['records_added']}")
    print(f"   Sample symbols: {result['symbol_list'][:10]}{'...' if len(result['symbol_list']) > 10 else ''}")

if __name__ == "__main__":
    main()
