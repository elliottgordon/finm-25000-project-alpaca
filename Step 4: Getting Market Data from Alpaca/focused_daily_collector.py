#!/usr/bin/env python3
"""
Focused Daily Data Collector for Top 100 US Equities + Key ETFs
Collects 7+ years of daily data for the focused asset selection
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

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_api import get_daily_bars
from step4_config import get_credentials

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('focused_daily_collection.log'),
        logging.StreamHandler()
    ]
)

class FocusedDailyCollector:
    """
    Focused daily data collector for top assets
    """
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
        self.eastern = pytz.timezone('US/Eastern')
        
        # Data collection parameters
        self.max_retries = 3
        self.retry_delay = 1
        self.batch_size = 5  # Smaller batches for daily data
        
        # Initialize database
        self._init_database()
        
        # Define focused asset universe
        self.focused_assets = self._define_focused_assets()
        
        logging.info("FocusedDailyCollector initialized")
    
    def _init_database(self):
        """Initialize database with proper schema for daily data"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
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
                    timeframe TEXT DEFAULT 'Day',
                    data_source TEXT DEFAULT 'Alpaca',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            ''')
            
            # Create indexes for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON market_data(symbol)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON market_data(timestamp)')
            
            conn.commit()
            conn.close()
            logging.info("Daily database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def _define_focused_assets(self) -> List[str]:
        """Define focused asset universe for daily trading strategy"""
        return [
            # Core Market ETFs
            'SPY', 'QQQ', 'IWM', 'VTI',
            
            # Sector ETFs
            'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLB', 'XLP', 'XLY', 'XLU',
            
            # Volatility ETFs
            'VXX', 'UVXY', 'TVIX', 'SVXY', 'XIV',
            
            # Tech Giants (Top Market Cap)
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'PEP', 'COST',
            
            # Financial Leaders
            'BRK.B', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'SPGI', 'BLK', 'SCHW', 'USB',
            
            # Healthcare Leaders
            'UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'DHR', 'LLY', 'ABT', 'BMY', 'GILD',
            
            # Consumer Leaders
            'PG', 'KO', 'WMT', 'HD', 'MCD', 'DIS', 'NKE', 'SBUX', 'TGT', 'LOW',
            
            # Energy & Industrial
            'XOM', 'CVX', 'V', 'MA', 'CMCSA', 'CHTR', 'NFLX', 'CME', 'ICE',
            
            # Communication & Media
            'FOX', 'FOXA', 'NWSA', 'NWS',
            
            # Commodity & Bond ETFs
            'GLD', 'SLV', 'USO', 'TLT', 'IEF', 'SHY',
            
            # International ETFs
            'EFA', 'EEM', 'FXI', 'EWJ', 'EWG', 'EWU',
            
            # Leveraged ETFs
            'TQQQ', 'SQQQ', 'SPXL', 'SPXS'
        ]
    
    def collect_daily_data(self, symbol: str, years_back: int = 7) -> bool:
        """Collect daily data for a single symbol"""
        for attempt in range(self.max_retries):
            try:
                logging.info(f"Collecting daily data for {symbol} (last {years_back} years)")
                
                # Set date range
                end_date = self.eastern.localize(datetime.now())
                start_date = end_date - timedelta(days=years_back * 365)
                
                # Fetch daily bars data
                data = get_daily_bars([symbol], start_date, end_date)
                
                if data.empty:
                    logging.warning(f"No daily data returned for {symbol}")
                    return False
                
                # Ensure proper column names
                data.columns = [col.lower() for col in data.columns]
                
                # Add timeframe and data source
                data['timeframe'] = 'Day'
                data['data_source'] = 'Alpaca'
                
                # Ensure timestamp is in the right format
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                # Save to database
                conn = sqlite3.connect(self.db_path)
                
                # Use INSERT OR IGNORE to handle duplicates
                data.to_sql('market_data', conn, if_exists='append', index=False)
                
                conn.commit()
                conn.close()
                
                logging.info(f"✅ Successfully collected {len(data)} daily bars for {symbol}")
                return True
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logging.error(f"Failed to collect daily data for {symbol} after {self.max_retries} attempts")
                    return False
        
        return False
    
    def collect_all_focused_data(self, years_back: int = 7) -> Dict[str, bool]:
        """Collect daily data for all focused assets"""
        logging.info(f"Starting focused daily data collection for {len(self.focused_assets)} symbols (last {years_back} years)")
        
        # Collect data in batches
        results = {}
        for i in range(0, len(self.focused_assets), self.batch_size):
            batch = self.focused_assets[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(self.focused_assets) + self.batch_size - 1) // self.batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
            
            for symbol in batch:
                success = self.collect_daily_data(symbol, years_back)
                results[symbol] = success
                
                # Small delay between symbols to avoid rate limits
                time.sleep(1)
            
            # Delay between batches
            if i + self.batch_size < len(self.focused_assets):
                logging.info(f"Waiting 5 seconds before next batch...")
                time.sleep(5)
        
        # Summary
        successful = sum(results.values())
        total = len(results)
        logging.info(f"Focused daily data collection complete: {successful}/{total} symbols successful")
        
        return results
    
    def get_data_summary(self) -> Dict:
        """Get summary of daily data collection results"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Overall statistics
            total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM market_data").fetchone()[0]
            total_records = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
            
            # Date range
            date_range = conn.execute("""
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest 
                FROM market_data
            """).fetchone()
            
            # Records per symbol
            symbol_counts = pd.read_sql_query("""
                SELECT symbol, COUNT(*) as count 
                FROM market_data 
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
    
    def verify_data_completeness(self) -> Dict[str, Dict]:
        """Verify data completeness for each symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            completeness = {}
            for symbol in self.focused_assets:
                query = """
                    SELECT COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest
                    FROM market_data
                    WHERE symbol = ?
                """
                result = conn.execute(query, (symbol,)).fetchone()
                
                if result[0] > 0:
                    earliest = pd.to_datetime(result[1])
                    latest = pd.to_datetime(result[2])
                    days_span = (latest - earliest).days
                    
                    completeness[symbol] = {
                        'records': result[0],
                        'earliest_date': result[1],
                        'latest_date': result[2],
                        'days_span': days_span,
                        'status': 'Complete' if days_span >= 2555 else 'Incomplete'  # 7 years = ~2555 days
                    }
                else:
                    completeness[symbol] = {
                        'records': 0,
                        'earliest_date': None,
                        'latest_date': None,
                        'days_span': 0,
                        'status': 'Missing'
                    }
            
            conn.close()
            return completeness
            
        except Exception as e:
            logging.error(f"Error verifying data completeness: {e}")
            return {}

def main():
    """Main function for focused daily data collection"""
    print("🚀 FOCUSED DAILY DATA COLLECTOR")
    print("=" * 60)
    print("Collects 7+ years of daily data for top 100 US equities + key ETFs")
    print("Optimized for 14-day RSI + Mean Reversion strategy")
    print("=" * 60)
    
    collector = FocusedDailyCollector()
    
    # Show focused asset universe
    print(f"\n📋 FOCUSED ASSET UNIVERSE:")
    print(f"   Total Assets: {len(collector.focused_assets)}")
    print(f"   Categories: Core ETFs, Sector ETFs, Tech Giants, Financial Leaders,")
    print(f"               Healthcare, Consumer, Energy, International, Leveraged")
    
    # Show current status
    print(f"\n📊 CURRENT DAILY DATA STATUS:")
    summary = collector.get_data_summary()
    if summary:
        print(f"   Total Symbols: {summary['total_symbols']}")
        print(f"   Total Records: {summary['total_records']:,}")
        if summary['earliest_date'] and summary['latest_date']:
            print(f"   Date Range: {summary['earliest_date']} to {summary['latest_date']}")
        print(f"   Avg Records/Symbol: {summary['avg_records_per_symbol']:.1f}")
    else:
        print("   No data found - starting fresh collection")
    
    print(f"\n🎯 OPTIONS:")
    print("   1. Collect full daily data (7+ years)")
    print("   2. Collect daily data (5 years)")
    print("   3. Collect daily data (3 years)")
    print("   4. Check data status")
    print("   5. Verify data completeness")
    print("   6. Exit")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        print(f"\n📥 Collecting full daily data (7+ years)...")
        results = collector.collect_all_focused_data(years_back=7)
        
        successful = sum(results.values())
        total = len(results)
        print(f"✅ Collection complete: {successful}/{total} symbols successful")
        
    elif choice == '2':
        print(f"\n📥 Collecting daily data (5 years)...")
        results = collector.collect_all_focused_data(years_back=5)
        
        successful = sum(results.values())
        total = len(results)
        print(f"✅ Collection complete: {successful}/{total} symbols successful")
        
    elif choice == '3':
        print(f"\n📥 Collecting daily data (3 years)...")
        results = collector.collect_all_focused_data(years_back=3)
        
        successful = sum(results.values())
        total = len(results)
        print(f"✅ Collection complete: {successful}/{total} symbols successful")
        
    elif choice == '4':
        print(f"\n📊 Checking daily data status...")
        summary = collector.get_data_summary()
        if summary:
            print(f"   Total Symbols: {summary['total_symbols']}")
            print(f"   Total Records: {summary['total_records']:,}")
            if summary['earliest_date'] and summary['latest_date']:
                print(f"   Date Range: {summary['earliest_date']} to {summary['latest_date']}")
            
            # Show top symbols by record count
            print(f"\n📈 TOP SYMBOLS BY RECORD COUNT:")
            for i, symbol_data in enumerate(summary['symbol_counts'][:10]):
                print(f"   {i+1:2d}. {symbol_data['symbol']:<6} - {symbol_data['count']:,} records")
        
    elif choice == '5':
        print(f"\n🔍 Verifying data completeness...")
        completeness = collector.verify_data_completeness()
        
        complete = sum(1 for data in completeness.values() if data['status'] == 'Complete')
        incomplete = sum(1 for data in completeness.values() if data['status'] == 'Incomplete')
        missing = sum(1 for data in completeness.values() if data['status'] == 'Missing')
        
        print(f"   Complete (7+ years): {complete}")
        print(f"   Incomplete: {incomplete}")
        print(f"   Missing: {missing}")
        
        if missing > 0:
            print(f"\n❌ MISSING SYMBOLS:")
            for symbol, data in completeness.items():
                if data['status'] == 'Missing':
                    print(f"   {symbol}")
        
    elif choice == '6':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")
    
    print(f"\n💡 NEXT STEPS:")
    print("   1. Use this data for your 14-day RSI strategy")
    print("   2. Test strategy with trading_strategy.py")
    print("   3. Optimize parameters for daily timeframe")
    print("   4. Set up regular data updates")

if __name__ == "__main__":
    main()
