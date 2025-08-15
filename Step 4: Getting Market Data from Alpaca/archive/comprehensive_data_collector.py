#!/usr/bin/env python3
"""
Comprehensive Data Collector for Step 4
Collects historical data for all assets in watchlist and sets up scheduled updates
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
from typing import List, Dict, Optional, Tuple
import schedule
import threading

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_api import get_daily_bars, make_client
from step4_config import get_credentials

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_collection.log'),
        logging.StreamHandler()
    ]
)

class ComprehensiveDataCollector:
    """
    Comprehensive data collection system for all assets in watchlist
    """
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
        self.watchlist_path = os.path.join(os.path.dirname(__file__), 'watchlist.txt')
        self.eastern = pytz.timezone('US/Eastern')
        
        # Data collection parameters
        self.max_retries = 3
        self.retry_delay = 2
        self.batch_size = 10  # Process symbols in batches to avoid rate limits
        
        # Initialize database
        self._init_database()
        
        logging.info("ComprehensiveDataCollector initialized")
    
    def _init_database(self):
        """Initialize database with proper schema"""
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
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            ''')
            
            # Create index for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON market_data(symbol)')
            
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def load_watchlist(self) -> List[str]:
        """Load symbols from watchlist file"""
        try:
            with open(self.watchlist_path, 'r') as f:
                lines = f.readlines()
            
            symbols = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('='):
                    symbols.append(line)
            
            logging.info(f"Loaded {len(symbols)} symbols from watchlist")
            return symbols
            
        except Exception as e:
            logging.error(f"Error loading watchlist: {e}")
            return []
    
    def get_existing_data_summary(self) -> Dict[str, Dict]:
        """Get summary of existing data for each symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT 
                    symbol,
                    COUNT(*) as record_count,
                    MIN(timestamp) as earliest_date,
                    MAX(timestamp) as latest_date
                FROM market_data 
                GROUP BY symbol
                ORDER BY symbol
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            summary = {}
            for _, row in df.iterrows():
                summary[row['symbol']] = {
                    'record_count': row['record_count'],
                    'earliest_date': row['earliest_date'],
                    'latest_date': row['latest_date']
                }
            
            return summary
            
        except Exception as e:
            logging.error(f"Error getting data summary: {e}")
            return {}
    
    def calculate_data_gaps(self, symbols: List[str]) -> Dict[str, Dict]:
        """Calculate data gaps for each symbol"""
        existing_data = self.get_existing_data_summary()
        gaps = {}
        
        today = self.eastern.localize(datetime.now())
        target_start = self.eastern.localize(datetime(2018, 1, 1))  # Target 7+ years of data
        
        for symbol in symbols:
            if symbol in existing_data:
                data = existing_data[symbol]
                latest_date = pd.to_datetime(data['latest_date'])
                
                # Ensure latest_date has timezone info
                if latest_date.tz is None:
                    latest_date = self.eastern.localize(latest_date.replace(tzinfo=None))
                
                # Check if we need to update
                days_since_update = (today - latest_date).days
                needs_update = days_since_update > 1  # Update if more than 1 day old
                
                gaps[symbol] = {
                    'status': 'needs_update' if needs_update else 'current',
                    'days_since_update': days_since_update,
                    'record_count': data['record_count'],
                    'earliest_date': data['earliest_date'],
                    'latest_date': data['latest_date']
                }
            else:
                # Symbol not in database
                gaps[symbol] = {
                    'status': 'missing',
                    'days_since_update': None,
                    'record_count': 0,
                    'earliest_date': None,
                    'latest_date': None
                }
        
        return gaps
    
    def collect_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> bool:
        """Collect historical data for a single symbol"""
        for attempt in range(self.max_retries):
            try:
                logging.info(f"Collecting data for {symbol} ({start_date.date()} to {end_date.date()})")
                
                # Fetch data from Alpaca
                data = get_daily_bars([symbol], start_date, end_date)
                
                if data.empty:
                    logging.warning(f"No data returned for {symbol}")
                    return False
                
                # Save to database
                conn = sqlite3.connect(self.db_path)
                
                # Use REPLACE to handle duplicates
                data.to_sql('market_data', conn, if_exists='replace', index=False)
                
                # Update the updated_at timestamp
                conn.execute('''
                    UPDATE market_data 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                ''', (symbol, start_date.isoformat(), end_date.isoformat()))
                
                conn.commit()
                conn.close()
                
                logging.info(f"✅ Successfully collected {len(data)} records for {symbol}")
                return True
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logging.error(f"Failed to collect data for {symbol} after {self.max_retries} attempts")
                    return False
        
        return False
    
    def collect_missing_data(self, symbols: List[str] = None) -> Dict[str, bool]:
        """Collect missing data for specified symbols or all symbols"""
        if symbols is None:
            symbols = self.load_watchlist()
        
        logging.info(f"Starting data collection for {len(symbols)} symbols")
        
        # Calculate data gaps
        gaps = self.calculate_data_gaps(symbols)
        
        # Determine what needs to be collected
        to_collect = []
        for symbol, gap_info in gaps.items():
            if gap_info['status'] in ['missing', 'needs_update']:
                to_collect.append(symbol)
        
        logging.info(f"Need to collect/update data for {len(to_collect)} symbols")
        
        # Set date range
        end_date = self.eastern.localize(datetime.now() - timedelta(days=1))
        start_date = self.eastern.localize(datetime(2018, 1, 1))
        
        # Collect data in batches
        results = {}
        for i in range(0, len(to_collect), self.batch_size):
            batch = to_collect[i:i + self.batch_size]
            logging.info(f"Processing batch {i//self.batch_size + 1}: {batch}")
            
            for symbol in batch:
                success = self.collect_historical_data(symbol, start_date, end_date)
                results[symbol] = success
                
                # Small delay between symbols to avoid rate limits
                time.sleep(0.5)
            
            # Delay between batches
            if i + self.batch_size < len(to_collect):
                time.sleep(2)
        
        # Summary
        successful = sum(results.values())
        total = len(results)
        logging.info(f"Data collection complete: {successful}/{total} symbols successful")
        
        return results
    
    def incremental_update(self) -> Dict[str, bool]:
        """Perform incremental update - only fetch new data since last update"""
        logging.info("Starting incremental data update")
        
        symbols = self.load_watchlist()
        gaps = self.calculate_data_gaps(symbols)
        
        # Only update symbols that need updating
        needs_update = [s for s, g in gaps.items() if g['status'] == 'needs_update']
        
        if not needs_update:
            logging.info("All data is current - no updates needed")
            return {}
        
        logging.info(f"Updating {len(needs_update)} symbols")
        
        # Update each symbol with recent data
        end_date = self.eastern.localize(datetime.now() - timedelta(days=1))
        results = {}
        
        for symbol in needs_update:
            gap_info = gaps[symbol]
            if gap_info['latest_date']:
                # Start from day after last update
                last_update = pd.to_datetime(gap_info['latest_date'])
                start_date = last_update + timedelta(days=1)
                
                if start_date <= end_date:
                    success = self.collect_historical_data(symbol, start_date, end_date)
                    results[symbol] = success
                else:
                    results[symbol] = True  # Already up to date
            else:
                # No existing data, collect full history
                start_date = self.eastern.localize(datetime(2018, 1, 1))
                success = self.collect_historical_data(symbol, start_date, end_date)
                results[symbol] = success
            
            time.sleep(0.5)  # Rate limiting
        
        return results
    
    def schedule_daily_update(self, time_str: str = "16:00"):
        """Schedule daily data update at specified time (default: 4 PM ET)"""
        schedule.every().day.at(time_str).do(self.incremental_update)
        logging.info(f"Scheduled daily update at {time_str} ET")
    
    def schedule_weekly_full_update(self, day: str = "sunday", time_str: str = "02:00"):
        """Schedule weekly full data collection on specified day and time"""
        getattr(schedule.every(), day).at(time_str).do(self.collect_missing_data)
        logging.info(f"Scheduled weekly full update every {day} at {time_str} ET")
    
    def run_scheduler(self, stop_event: threading.Event = None):
        """Run the scheduler in a loop"""
        logging.info("Starting scheduler...")
        
        while True:
            if stop_event and stop_event.is_set():
                logging.info("Scheduler stopped")
                break
            
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def get_data_quality_report(self) -> Dict:
        """Generate comprehensive data quality report"""
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
            
            # Symbols with most/least data
            symbol_counts = pd.read_sql_query("""
                SELECT symbol, COUNT(*) as count 
                FROM market_data 
                GROUP BY symbol 
                ORDER BY count DESC
            """, conn)
            
            conn.close()
            
            report = {
                'total_symbols': total_symbols,
                'total_records': total_records,
                'earliest_date': date_range[0],
                'latest_date': date_range[1],
                'avg_records_per_symbol': total_records / total_symbols if total_symbols > 0 else 0,
                'top_symbols': symbol_counts.head(10).to_dict('records'),
                'bottom_symbols': symbol_counts.tail(10).to_dict('records'),
                'data_completeness': self._calculate_completeness()
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error generating quality report: {e}")
            return {}
    
    def _calculate_completeness(self) -> float:
        """Calculate overall data completeness percentage"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Count symbols with recent data (within last 2 days)
            recent_cutoff = (datetime.now() - timedelta(days=2)).isoformat()
            recent_symbols = conn.execute("""
                SELECT COUNT(DISTINCT symbol) 
                FROM market_data 
                WHERE timestamp >= ?
            """, (recent_cutoff,)).fetchone()[0]
            
            total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM market_data").fetchone()[0]
            conn.close()
            
            return (recent_symbols / total_symbols * 100) if total_symbols > 0 else 0
            
        except Exception as e:
            logging.error(f"Error calculating completeness: {e}")
            return 0.0

def main():
    """Main function for data collection"""
    collector = ComprehensiveDataCollector()
    
    print("🚀 COMPREHENSIVE DATA COLLECTION SYSTEM")
    print("=" * 60)
    
    # Show current data status
    print("\n📊 CURRENT DATA STATUS:")
    gaps = collector.calculate_data_gaps(collector.load_watchlist())
    
    missing = sum(1 for g in gaps.values() if g['status'] == 'missing')
    needs_update = sum(1 for g in gaps.values() if g['status'] == 'needs_update')
    current = sum(1 for g in gaps.values() if g['status'] == 'current')
    
    print(f"   Total Symbols: {len(gaps)}")
    print(f"   Missing Data: {missing}")
    print(f"   Needs Update: {needs_update}")
    print(f"   Current: {current}")
    
    # Data quality report
    print("\n🔍 DATA QUALITY REPORT:")
    quality_report = collector.get_data_quality_report()
    if quality_report:
        print(f"   Total Records: {quality_report['total_records']:,}")
        print(f"   Date Range: {quality_report['earliest_date']} to {quality_report['latest_date']}")
        print(f"   Avg Records/Symbol: {quality_report['avg_records_per_symbol']:.1f}")
        print(f"   Data Completeness: {quality_report['data_completeness']:.1f}%")
    
    # Ask user what to do
    print("\n🎯 OPTIONS:")
    print("   1. Collect missing data")
    print("   2. Perform incremental update")
    print("   3. Schedule daily updates")
    print("   4. Schedule weekly full updates")
    print("   5. Run scheduler (continuous)")
    print("   6. Exit")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        print("\n📥 Collecting missing data...")
        results = collector.collect_missing_data()
        print(f"✅ Completed: {sum(results.values())}/{len(results)} successful")
        
    elif choice == '2':
        print("\n🔄 Performing incremental update...")
        results = collector.incremental_update()
        print(f"✅ Completed: {sum(results.values())}/{len(results)} successful")
        
    elif choice == '3':
        time_str = input("Enter time for daily updates (HH:MM, default 16:00): ").strip() or "16:00"
        collector.schedule_daily_update(time_str)
        print(f"✅ Daily updates scheduled at {time_str} ET")
        
    elif choice == '4':
        day = input("Enter day for weekly updates (default sunday): ").strip() or "sunday"
        time_str = input("Enter time for weekly updates (HH:MM, default 02:00): ").strip() or "02:00"
        collector.schedule_weekly_full_update(day, time_str)
        print(f"✅ Weekly updates scheduled every {day} at {time_str} ET")
        
    elif choice == '5':
        print("\n⏰ Starting scheduler (press Ctrl+C to stop)...")
        try:
            collector.run_scheduler()
        except KeyboardInterrupt:
            print("\n⏹️  Scheduler stopped")
            
    elif choice == '6':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
