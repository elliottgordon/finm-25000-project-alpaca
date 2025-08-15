#!/usr/bin/env python3
"""
Simple Data Collector for Missing Symbols
Works with existing database schema and efficiently collects missing data
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import logging
from typing import List, Dict

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_api import get_daily_bars

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_data_collection.log'),
        logging.StreamHandler()
    ]
)

class SimpleDataCollector:
    """
    Simple data collector for missing symbols
    """
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
        self.watchlist_path = os.path.join(os.path.dirname(__file__), 'watchlist.txt')
        self.eastern = pytz.timezone('US/Eastern')
        
        # Data collection parameters
        self.max_retries = 3
        self.retry_delay = 1
        self.batch_size = 20  # Larger batch size for efficiency
        
        logging.info("SimpleDataCollector initialized")
    
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
    
    def get_missing_symbols(self) -> List[str]:
        """Get list of symbols that are missing from database"""
        try:
            watchlist_symbols = self.load_watchlist()
            
            conn = sqlite3.connect(self.db_path)
            existing_symbols = set()
            
            # Get existing symbols
            query = "SELECT DISTINCT symbol FROM market_data"
            results = conn.execute(query).fetchall()
            existing_symbols = {row[0] for row in results}
            
            conn.close()
            
            # Find missing symbols
            missing_symbols = [s for s in watchlist_symbols if s not in existing_symbols]
            
            logging.info(f"Found {len(missing_symbols)} missing symbols out of {len(watchlist_symbols)} total")
            return missing_symbols
            
        except Exception as e:
            logging.error(f"Error getting missing symbols: {e}")
            return []
    
    def collect_symbol_data(self, symbol: str) -> bool:
        """Collect data for a single symbol"""
        for attempt in range(self.max_retries):
            try:
                logging.info(f"Collecting data for {symbol} (attempt {attempt + 1})")
                
                # Set date range (last 2 years for efficiency)
                end_date = self.eastern.localize(datetime.now() - timedelta(days=1))
                start_date = self.eastern.localize(datetime(2023, 1, 1))
                
                # Fetch data from Alpaca
                data = get_daily_bars([symbol], start_date, end_date)
                
                if data.empty:
                    logging.warning(f"No data returned for {symbol}")
                    return False
                
                # Save to database
                conn = sqlite3.connect(self.db_path)
                
                # Use INSERT OR IGNORE to handle duplicates
                data.to_sql('market_data', conn, if_exists='append', index=False)
                
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
    
    def collect_all_missing_data(self) -> Dict[str, bool]:
        """Collect data for all missing symbols"""
        missing_symbols = self.get_missing_symbols()
        
        if not missing_symbols:
            logging.info("No missing symbols to collect!")
            return {}
        
        logging.info(f"Starting data collection for {len(missing_symbols)} missing symbols")
        
        # Collect data in batches
        results = {}
        for i in range(0, len(missing_symbols), self.batch_size):
            batch = missing_symbols[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(missing_symbols) + self.batch_size - 1) // self.batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
            
            for symbol in batch:
                success = self.collect_symbol_data(symbol)
                results[symbol] = success
                
                # Small delay between symbols to avoid rate limits
                time.sleep(0.3)
            
            # Delay between batches
            if i + self.batch_size < len(missing_symbols):
                logging.info(f"Waiting 2 seconds before next batch...")
                time.sleep(2)
        
        # Summary
        successful = sum(results.values())
        total = len(results)
        logging.info(f"Data collection complete: {successful}/{total} symbols successful")
        
        return results
    
    def get_collection_summary(self) -> Dict:
        """Get summary of data collection results"""
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
            
            conn.close()
            
            summary = {
                'total_symbols': total_symbols,
                'total_records': total_records,
                'earliest_date': date_range[0],
                'latest_date': date_range[1],
                'avg_records_per_symbol': total_records / total_symbols if total_symbols > 0 else 0
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"Error generating summary: {e}")
            return {}

def main():
    """Main function"""
    print("🚀 SIMPLE DATA COLLECTOR FOR MISSING SYMBOLS")
    print("=" * 60)
    
    collector = SimpleDataCollector()
    
    # Show current status
    print("\n📊 CURRENT DATA STATUS:")
    summary = collector.get_collection_summary()
    if summary:
        print(f"   Total Symbols: {summary['total_symbols']}")
        print(f"   Total Records: {summary['total_records']:,}")
        print(f"   Date Range: {summary['earliest_date']} to {summary['latest_date']}")
        print(f"   Avg Records/Symbol: {summary['avg_records_per_symbol']:.1f}")
    
    # Check for missing symbols
    print("\n🔍 CHECKING FOR MISSING SYMBOLS...")
    missing_symbols = collector.get_missing_symbols()
    
    if missing_symbols:
        print(f"   Missing Symbols: {len(missing_symbols)}")
        print(f"   Examples: {', '.join(missing_symbols[:10])}")
        if len(missing_symbols) > 10:
            print(f"   ... and {len(missing_symbols) - 10} more")
        
        print(f"\n🎯 STARTING DATA COLLECTION...")
        print(f"   This will collect data for {len(missing_symbols)} missing symbols")
        print(f"   Estimated time: {len(missing_symbols) * 0.5 / 60:.1f} minutes")
        
        # Ask for confirmation
        confirm = input(f"\nProceed with data collection? (y/n): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            print(f"\n📥 Starting data collection...")
            results = collector.collect_all_missing_data()
            
            successful = sum(results.values())
            total = len(results)
            print(f"\n✅ COLLECTION COMPLETE!")
            print(f"   Successful: {successful}/{total}")
            print(f"   Failed: {total - successful}")
            
            if successful < total:
                failed_symbols = [s for s, success in results.items() if not success]
                print(f"   Failed symbols: {', '.join(failed_symbols[:20])}")
                if len(failed_symbols) > 20:
                    print(f"   ... and {len(failed_symbols) - 20} more")
            
            # Final summary
            final_summary = collector.get_collection_summary()
            if final_summary:
                print(f"\n📊 FINAL STATUS:")
                print(f"   Total Symbols: {final_summary['total_symbols']}")
                print(f"   Total Records: {final_summary['total_records']:,}")
                print(f"   Data Completeness: {len(missing_symbols) - (total - successful)}/{len(missing_symbols)} symbols added")
        else:
            print("❌ Data collection cancelled")
    else:
        print("✅ No missing symbols found!")
        print("   All watchlist symbols are present in the database")
    
    print(f"\n💡 NEXT STEPS:")
    print("   1. Run 'python quick_data_check.py' to verify data completeness")
    print("   2. Run 'python data_update_scheduler.py' to set up automatic updates")
    print("   3. Return to Step 7 to test your strategy with complete data!")

if __name__ == "__main__":
    main()
