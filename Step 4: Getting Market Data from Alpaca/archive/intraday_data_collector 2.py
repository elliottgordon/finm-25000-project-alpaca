#!/usr/bin/env python3
"""
Intraday Data Collector for Short-term RSI/Mean Reversion Strategy
Collects minute-by-minute data for focused asset selection
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
import logging
from typing import List, Dict, Optional
import threading

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_api import get_minute_bars, make_client
from step4_config import get_credentials

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intraday_collection.log'),
        logging.StreamHandler()
    ]
)

class IntradayDataCollector:
    """
    Intraday data collector for short-term trading strategies
    """
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'intraday_market_data.db')
        self.watchlist_path = os.path.join(os.path.dirname(__file__), 'intraday_watchlist.txt')
        self.eastern = pytz.timezone('US/Eastern')
        
        # Data collection parameters
        self.max_retries = 3
        self.retry_delay = 1
        self.batch_size = 10  # Smaller batches for intraday data
        
        # Initialize database
        self._init_database()
        
        logging.info("IntradayDataCollector initialized")
    
    def _init_database(self):
        """Initialize database with proper schema for intraday data"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS intraday_market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER,
                    trade_count INTEGER,
                    vwap REAL,
                    timeframe TEXT DEFAULT 'Minute',
                    data_source TEXT DEFAULT 'Alpaca',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            ''')
            
            # Create indexes for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON intraday_market_data(symbol, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON intraday_market_data(symbol)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON intraday_market_data(timestamp)')
            
            conn.commit()
            conn.close()
            logging.info("Intraday database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def load_intraday_watchlist(self) -> List[str]:
        """Load symbols from intraday watchlist file"""
        try:
            with open(self.watchlist_path, 'r') as f:
                lines = f.readlines()
            
            symbols = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('='):
                    # Extract symbol (everything before the first space)
                    symbol = line.split()[0]
                    symbols.append(symbol)
            
            logging.info(f"Loaded {len(symbols)} symbols from intraday watchlist")
            return symbols
            
        except Exception as e:
            logging.error(f"Error loading intraday watchlist: {e}")
            return []
    
    def get_minute_bars_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get minute bars data for a symbol"""
        try:
            # Use the existing get_minute_bars function from step4_api
            data = get_minute_bars([symbol], start_date, end_date)
            
            if not data.empty:
                # Ensure proper column names
                data.columns = [col.lower() for col in data.columns]
                
                # Add timeframe and data source
                data['timeframe'] = 'Minute'
                data['data_source'] = 'Alpaca'
                
                # Ensure timestamp is in the right format
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                logging.info(f"Retrieved {len(data)} minute bars for {symbol}")
                return data
            else:
                logging.warning(f"No minute bars data returned for {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            logging.error(f"Error getting minute bars for {symbol}: {e}")
            return pd.DataFrame()
    
    def collect_intraday_data(self, symbol: str, days_back: int = 700) -> bool:
        """Collect intraday data for a single symbol"""
        for attempt in range(self.max_retries):
            try:
                logging.info(f"Collecting intraday data for {symbol} (last {days_back} days)")
                
                # Set date range
                end_date = self.eastern.localize(datetime.now())
                start_date = end_date - timedelta(days=days_back)
                
                # Fetch minute bars data
                data = self.get_minute_bars_data(symbol, start_date, end_date)
                
                if data.empty:
                    logging.warning(f"No intraday data returned for {symbol}")
                    return False
                
                # Save to database
                conn = sqlite3.connect(self.db_path)
                
                # Use INSERT OR IGNORE to handle duplicates
                data.to_sql('intraday_market_data', conn, if_exists='append', index=False)
                
                conn.commit()
                conn.close()
                
                logging.info(f"✅ Successfully collected {len(data)} minute bars for {symbol}")
                return True
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logging.error(f"Failed to collect intraday data for {symbol} after {self.max_retries} attempts")
                    return False
        
        return False
    
    def collect_all_intraday_data(self, days_back: int = 30) -> Dict[str, bool]:
        """Collect intraday data for all symbols in watchlist"""
        symbols = self.load_intraday_watchlist()
        
        if not symbols:
            logging.error("No symbols found in intraday watchlist")
            return {}
        
        logging.info(f"Starting intraday data collection for {len(symbols)} symbols (last {days_back} days)")
        
        # Collect data in batches
        results = {}
        for i in range(0, len(symbols), self.batch_size):
            batch = symbols[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
            
            for symbol in batch:
                success = self.collect_intraday_data(symbol, days_back)
                results[symbol] = success
                
                # Small delay between symbols to avoid rate limits
                time.sleep(0.5)
            
            # Delay between batches
            if i + self.batch_size < len(symbols):
                logging.info(f"Waiting 3 seconds before next batch...")
                time.sleep(3)
        
        # Summary
        successful = sum(results.values())
        total = len(results)
        logging.info(f"Intraday data collection complete: {successful}/{total} symbols successful")
        
        return results
    
    def get_data_summary(self) -> Dict:
        """Get summary of intraday data collection results"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Overall statistics
            total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM intraday_market_data").fetchone()[0]
            total_records = conn.execute("SELECT COUNT(*) FROM intraday_market_data").fetchone()[0]
            
            # Date range
            date_range = conn.execute("""
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest 
                FROM intraday_market_data
            """).fetchone()
            
            # Records per symbol
            symbol_counts = pd.read_sql_query("""
                SELECT symbol, COUNT(*) as count 
                FROM intraday_market_data 
                GROUP BY symbol 
                ORDER BY count DESC
            """, conn)
            
            conn.close()
            
            summary = {
                'total_symbols': total_symbols,
                'total_records': total_records,
                'earliest_date': date_range[0],
                'latest_date': date_range[1],
                'avg_records_per_symbol': total_records / total_symbols if total_symbols > 0 else 0,
                'symbol_counts': symbol_counts.to_dict('records')
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"Error generating summary: {e}")
            return {}
    
    def update_recent_data(self, symbols: List[str] = None, hours_back: int = 24) -> Dict[str, bool]:
        """Update recent intraday data for specified symbols"""
        if symbols is None:
            symbols = self.load_intraday_watchlist()
        
        logging.info(f"Updating recent intraday data for {len(symbols)} symbols (last {hours_back} hours)")
        
        # Set date range
        end_date = self.eastern.localize(datetime.now())
        start_date = end_date - timedelta(hours=hours_back)
        
        results = {}
        for symbol in symbols:
            try:
                # Get recent data
                data = self.get_minute_bars_data(symbol, start_date, end_date)
                
                if not data.empty:
                    # Save to database
                    conn = sqlite3.connect(self.db_path)
                    data.to_sql('intraday_market_data', conn, if_exists='append', index=False)
                    conn.commit()
                    conn.close()
                    
                    results[symbol] = True
                    logging.info(f"✅ Updated {len(data)} recent minute bars for {symbol}")
                else:
                    results[symbol] = False
                    logging.warning(f"No recent data for {symbol}")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                logging.error(f"Error updating recent data for {symbol}: {e}")
                results[symbol] = False
        
        return results

def main():
    """Main function for intraday data collection"""
    print("🚀 INTRADAY DATA COLLECTOR")
    print("=" * 50)
    print("Collects minute-by-minute data for short-term RSI/Mean Reversion strategy")
    print("=" * 50)
    
    collector = IntradayDataCollector()
    
    # Show current status
    print("\n📊 CURRENT INTRADAY DATA STATUS:")
    summary = collector.get_data_summary()
    if summary:
        print(f"   Total Symbols: {summary['total_symbols']}")
        print(f"   Total Records: {summary['total_records']:,}")
        print(f"   Date Range: {summary['earliest_date']} to {summary['latest_date']}")
        print(f"   Avg Records/Symbol: {summary['avg_records_per_symbol']:.1f}")
    else:
        print("   No data found - starting fresh collection")
    
    # Load watchlist
    symbols = collector.load_intraday_watchlist()
    print(f"\n📋 Intraday Watchlist: {len(symbols)} symbols")
    
    print(f"\n🎯 OPTIONS:")
    print("   1. Collect full intraday data (last 700 days)")
    print("   2. Collect full intraday data (last 7 days)")
    print("   3. Update recent data (last 24 hours)")
    print("   4. Check data status")
    print("   5. Exit")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == '1':
        print(f"\n📥 Collecting full intraday data (last 30 days)...")
        results = collector.collect_all_intraday_data(days_back=30)
        
        successful = sum(results.values())
        total = len(results)
        print(f"✅ Collection complete: {successful}/{total} symbols successful")
        
    elif choice == '2':
        print(f"\n📥 Collecting full intraday data (last 7 days)...")
        results = collector.collect_all_intraday_data(days_back=7)
        
        successful = sum(results.values())
        total = len(results)
        print(f"✅ Collection complete: {successful}/{total} symbols successful")
        
    elif choice == '3':
        print(f"\n🔄 Updating recent intraday data (last 24 hours)...")
        results = collector.update_recent_data(hours_back=24)
        
        successful = sum(results.values())
        total = len(results)
        print(f"✅ Update complete: {successful}/{total} symbols successful")
        
    elif choice == '4':
        print(f"\n📊 Checking intraday data status...")
        summary = collector.get_data_summary()
        if summary:
            print(f"   Total Symbols: {summary['total_symbols']}")
            print(f"   Total Records: {summary['total_records']:,}")
            print(f"   Date Range: {summary['earliest_date']} to {summary['latest_date']}")
            
            # Show top symbols by record count
            print(f"\n📈 TOP SYMBOLS BY RECORD COUNT:")
            for i, symbol_data in enumerate(summary['symbol_counts'][:10]):
                print(f"   {i+1:2d}. {symbol_data['symbol']:<6} - {symbol_data['count']:,} records")
        
    elif choice == '5':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")
    
    print(f"\n💡 NEXT STEPS:")
    print("   1. Use this data for your 3-5 day RSI strategy")
    print("   2. Set up regular updates for fresh intraday data")
    print("   3. Return to Step 7 to test your intraday strategy!")

if __name__ == "__main__":
    main()
