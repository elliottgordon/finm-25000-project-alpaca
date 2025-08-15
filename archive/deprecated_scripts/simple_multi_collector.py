# Simple Multi-Asset Data Collector
# Based on your existing working data_saver.py but expanded for multiple assets

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging
import time

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from Alpaca_API import ALPACA_KEY, ALPACA_SECRET
from asset_universe import get_etf_universe, get_priority_universe

# Import Alpaca API
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.enums import Adjustment
from alpaca.data.timeframe import TimeFrame

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_asset_simple.log'),
        logging.StreamHandler()
    ]
)

class SimpleMultiAssetCollector:
    """Simple multi-asset data collector based on your working data_saver.py"""
    
    def __init__(self, db_path='../Step 5: Saving Market Data/market_data.db'):
        self.client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
        self.db_path = db_path
        self.eastern = pytz.timezone('US/Eastern')
        
        logging.info("Simple Multi-Asset Collector initialized")
    
    def get_historical_data(self, symbols, start, end):
        """Get historical data for multiple symbols (based on your working method)"""
        all_data = []
        
        for symbol in symbols:
            try:
                logging.info(f"Fetching data for {symbol}...")
                
                request_params = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=TimeFrame.Day,
                    start=start,
                    end=end,
                    adjustment=Adjustment.ALL
                )
                
                bars = self.client.get_stock_bars(request_params).df.reset_index()
                
                if not bars.empty:
                    all_data.append(bars)
                    logging.info(f"✅ {symbol}: {len(bars)} records retrieved")
                    time.sleep(0.1)  # Small delay to be respectful to API
                else:
                    logging.warning(f"⚠️ {symbol}: No data received")
                    
            except Exception as e:
                logging.error(f"❌ {symbol}: Error - {str(e)}")
                continue
        
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            return combined_data
        else:
            return pd.DataFrame()
    
    def insert_data_frame(self, data, engine):
        """Insert data into database (your existing method)"""
        data.to_sql('market_data', engine, if_exists='append', index=False)
    
    def get_existing_symbols(self):
        """Get symbols that already exist in database"""
        try:
            import sqlalchemy
            engine = sqlalchemy.create_engine(f'sqlite:///{self.db_path}')
            
            query = "SELECT DISTINCT symbol FROM market_data"
            result = pd.read_sql(query, engine)
            return result['symbol'].tolist()
        except:
            return []
    
    def get_latest_timestamp(self, engine, symbol=None):
        """Get latest timestamp for a symbol or overall"""
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
    
    def run_collection(self, symbol_list=None, lookback_years=3):
        """Run data collection for specified symbols"""
        import sqlalchemy
        
        if symbol_list is None:
            # Use ETF universe as default
            symbol_list = get_etf_universe()[:20]  # Start with first 20 ETFs
        
        logging.info(f"Starting collection for {len(symbol_list)} symbols: {symbol_list}")
        
        # Set date range
        eastern = pytz.timezone('US/Eastern')
        end = eastern.localize(datetime.now() - timedelta(days=1))
        start = eastern.localize(datetime.now() - timedelta(days=lookback_years*365))
        
        engine = sqlalchemy.create_engine(f'sqlite:///{self.db_path}')
        
        # Process symbols in batches
        batch_size = 5
        total_records = 0
        
        for i in range(0, len(symbol_list), batch_size):
            batch = symbol_list[i:i+batch_size]
            
            logging.info(f"Processing batch {i//batch_size + 1}: {batch}")
            
            try:
                # Get historical data for batch
                data = self.get_historical_data(batch, start, end)
                
                if not data.empty:
                    # Insert data
                    self.insert_data_frame(data, engine)
                    batch_records = len(data)
                    total_records += batch_records
                    
                    logging.info(f"✅ Batch complete: {batch_records} records inserted")
                else:
                    logging.warning(f"⚠️ No data for batch: {batch}")
                
                # Delay between batches
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"❌ Batch failed: {str(e)}")
                continue
        
        logging.info(f"🎉 Collection complete! Total records added: {total_records}")
        return total_records

def main():
    """Main function to run expanded data collection"""
    collector = SimpleMultiAssetCollector()
    
    print("🚀 Starting Multi-Asset Data Collection")
    print("=" * 60)
    
    # Get priority universe
    priority_universe = get_priority_universe()
    
    # Start with Tier 1 ETFs (most reliable)
    tier_1_symbols = priority_universe['tier_1_etfs']
    print(f"\n📊 Collecting Tier 1 ETFs ({len(tier_1_symbols)} symbols)")
    print(f"Symbols: {tier_1_symbols}")
    
    # Run collection
    total_records = collector.run_collection(tier_1_symbols, lookback_years=2)
    
    # Get summary
    existing_symbols = collector.get_existing_symbols()
    print(f"\n📈 Collection Summary:")
    print(f"   Total symbols in database: {len(existing_symbols)}")
    print(f"   Records added this session: {total_records}")
    print(f"   Database path: {collector.db_path}")
    
    # Show sample of symbols collected
    if existing_symbols:
        print(f"\n🔤 Sample symbols in database:")
        print(f"   {', '.join(existing_symbols[:15])}{'...' if len(existing_symbols) > 15 else ''}")

if __name__ == "__main__":
    main()
