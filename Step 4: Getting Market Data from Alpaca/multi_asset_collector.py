# Enhanced Multi-Asset Data Collector with Async Processing
# Collects data for expanded universe of assets for RSI + Mean Reversion Strategy

import os
import sys
import asyncio
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from Alpaca_API import ALPACA_KEY, ALPACA_SECRET
from asset_universe import get_priority_universe, get_all_symbols, get_etf_universe

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
        logging.FileHandler('multi_asset_collector.log'),
        logging.StreamHandler()
    ]
)

class MultiAssetDataCollector:
    """
    Enhanced data collector for multiple assets with async processing
    Optimized for RSI + Mean Reversion strategy data needs
    """
    
    def __init__(self, db_path='../Step 5: Saving Market Data/market_data.db'):
        self.client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
        self.db_path = db_path
        self.eastern = pytz.timezone('US/Eastern')
        
        # Rate limiting parameters
        self.max_concurrent_requests = 5  # Alpaca rate limits
        self.request_delay = 0.2  # 200ms between requests
        
        logging.info("Multi-Asset Data Collector initialized")
    
    def create_enhanced_database(self):
        """Create enhanced database schema for multiple assets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced market data table
        cursor.execute('''
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
        
        # Asset metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asset_metadata (
                symbol TEXT PRIMARY KEY,
                asset_class TEXT,
                sector TEXT,
                first_trade_date TEXT,
                last_update TEXT,
                total_records INTEGER DEFAULT 0,
                data_quality_score REAL DEFAULT 0.0,
                mean_reversion_score REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Data collection log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                collection_date TEXT,
                records_added INTEGER,
                success BOOLEAN,
                error_message TEXT,
                execution_time_seconds REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON market_data(symbol, timeframe)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_collection_date ON collection_log(collection_date)')
        
        conn.commit()
        conn.close()
        
        logging.info("Enhanced database schema created/updated")
    
    def get_symbols_needing_update(self, symbols=None, max_age_days=1):
        """Get list of symbols that need data updates"""
        if symbols is None:
            symbols = get_etf_universe()  # Start with ETF universe
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        symbols_to_update = []
        cutoff_date = (datetime.now() - timedelta(days=max_age_days)).strftime('%Y-%m-%d')
        
        for symbol in symbols:
            # Check if symbol has recent data
            cursor.execute('''
                SELECT MAX(timestamp) as last_date, COUNT(*) as record_count
                FROM market_data 
                WHERE symbol = ? AND timeframe = 'Day'
            ''', (symbol,))
            
            result = cursor.fetchone()
            last_date, record_count = result if result else (None, 0)
            
            needs_update = False
            if last_date is None:
                needs_update = True
                reason = "No data found"
            elif last_date < cutoff_date:
                needs_update = True
                reason = f"Data older than {max_age_days} days"
            elif record_count < 100:  # Ensure minimum data for strategy
                needs_update = True
                reason = f"Insufficient data ({record_count} records)"
            else:
                reason = "Up to date"
            
            if needs_update:
                symbols_to_update.append(symbol)
                logging.info(f"{symbol}: {reason} - queued for update")
            else:
                logging.debug(f"{symbol}: {reason}")
        
        conn.close()
        return symbols_to_update
    
    def collect_symbol_data(self, symbol, start_date=None, end_date=None):
        """Collect historical data for a single symbol"""
        start_time = time.time()
        
        try:
            # Default date range: last 3 years for new symbols, last 30 days for updates
            if start_date is None:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(timestamp) FROM market_data WHERE symbol = ?', (symbol,))
                last_date = cursor.fetchone()[0]
                conn.close()
                
                if last_date:
                    start_date = datetime.strptime(last_date.split()[0], '%Y-%m-%d') + timedelta(days=1)
                else:
                    start_date = datetime.now() - timedelta(days=1095)  # 3 years
            
            if end_date is None:
                end_date = datetime.now() - timedelta(days=1)  # Yesterday
            
            # Make timezone-aware
            if start_date.tzinfo is None:
                start_date = self.eastern.localize(start_date)
            if end_date.tzinfo is None:
                end_date = self.eastern.localize(end_date)
            
            # Get data from Alpaca
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],  # Pass as list
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
                adjustment=Adjustment.ALL
            )
            
            logging.info(f"Requesting data for {symbol} from {start_date.date()} to {end_date.date()}")
            bars = self.client.get_stock_bars(request_params)
            
            # Convert to DataFrame
            if hasattr(bars, 'df'):
                data = bars.df.reset_index()
            else:
                # Handle raw data format
                data_list = []
                for bar in bars:
                    data_list.append({
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume,
                        'trade_count': getattr(bar, 'trade_count', None),
                        'vwap': getattr(bar, 'vwap', None)
                    })
                data = pd.DataFrame(data_list)
            
            if data.empty:
                logging.warning(f"No data received for {symbol}")
                return 0
            
            # Insert data into database
            records_added = self.insert_symbol_data(symbol, data)
            execution_time = time.time() - start_time
            
            # Log collection success
            self.log_collection(symbol, records_added, True, None, execution_time)
            
            logging.info(f"✅ {symbol}: {records_added} records added in {execution_time:.2f}s")
            return records_added
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Log collection failure
            self.log_collection(symbol, 0, False, error_msg, execution_time)
            
            logging.error(f"❌ {symbol}: Failed - {error_msg}")
            return 0
    
    def insert_symbol_data(self, symbol, data):
        """Insert data for a symbol with duplicate handling"""
        if data.empty:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        
        # Prepare data
        data['symbol'] = symbol
        data['timeframe'] = 'Day'
        data['data_source'] = 'Alpaca'
        data['created_at'] = datetime.now().isoformat()
        data['updated_at'] = datetime.now().isoformat()
        
        # Select required columns
        columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 
                  'volume', 'trade_count', 'vwap', 'timeframe', 'data_source', 
                  'created_at', 'updated_at']
        
        insert_data = data[columns].copy()
        
        # Insert with conflict resolution
        insert_data.to_sql('market_data', conn, if_exists='append', index=False)
        
        conn.close()
        return len(insert_data)
    
    def log_collection(self, symbol, records_added, success, error_message, execution_time):
        """Log collection attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO collection_log 
            (symbol, collection_date, records_added, success, error_message, execution_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, datetime.now().isoformat(), records_added, success, error_message, execution_time))
        
        conn.commit()
        conn.close()
    
    async def collect_multiple_symbols_async(self, symbols, max_workers=5):
        """Collect data for multiple symbols with async processing"""
        logging.info(f"Starting async collection for {len(symbols)} symbols")
        
        # Use ThreadPoolExecutor for I/O bound tasks
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.collect_symbol_data, symbol): symbol 
                for symbol in symbols
            }
            
            total_records = 0
            successful_symbols = []
            failed_symbols = []
            
            # Process completed tasks
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                
                try:
                    records_added = future.result()
                    total_records += records_added
                    successful_symbols.append(symbol)
                    
                    # Add delay to respect rate limits
                    await asyncio.sleep(self.request_delay)
                    
                except Exception as e:
                    logging.error(f"Exception for {symbol}: {e}")
                    failed_symbols.append(symbol)
        
        logging.info(f"Collection complete: {len(successful_symbols)} successful, {len(failed_symbols)} failed")
        logging.info(f"Total records added: {total_records}")
        
        return {
            'total_records': total_records,
            'successful_symbols': successful_symbols,
            'failed_symbols': failed_symbols
        }
    
    def update_asset_metadata(self, symbols):
        """Update metadata for collected symbols"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for symbol in symbols:
            # Get basic stats
            cursor.execute('''
                SELECT COUNT(*) as total_records,
                       MIN(timestamp) as first_date,
                       MAX(timestamp) as last_date
                FROM market_data 
                WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            total_records, first_date, last_date = result if result else (0, None, None)
            
            # Calculate data quality score (placeholder)
            data_quality_score = min(1.0, total_records / 500)  # 500+ records = perfect score
            
            # Insert or update metadata
            cursor.execute('''
                INSERT OR REPLACE INTO asset_metadata 
                (symbol, total_records, first_trade_date, last_update, data_quality_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, total_records, first_date, last_date, data_quality_score))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Updated metadata for {len(symbols)} symbols")
    
    def get_collection_summary(self):
        """Get summary of data collection status"""
        conn = sqlite3.connect(self.db_path)
        
        # Asset summary
        asset_summary = pd.read_sql_query('''
            SELECT symbol, total_records, last_update, data_quality_score
            FROM asset_metadata
            ORDER BY total_records DESC
        ''', conn)
        
        # Recent collection log
        recent_log = pd.read_sql_query('''
            SELECT symbol, collection_date, records_added, success, error_message
            FROM collection_log
            WHERE collection_date >= date('now', '-7 days')
            ORDER BY collection_date DESC
            LIMIT 50
        ''', conn)
        
        # Overall stats
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM market_data')
        unique_symbols = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM market_data')
        total_records = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'unique_symbols': unique_symbols,
            'total_records': total_records,
            'asset_summary': asset_summary,
            'recent_log': recent_log
        }

async def main():
    """Main async function for data collection"""
    collector = MultiAssetDataCollector()
    
    # Initialize database
    collector.create_enhanced_database()
    
    # Get priority symbols (start with ETFs)
    priority_universe = get_priority_universe()
    
    print("🚀 Starting Multi-Asset Data Collection")
    print("=" * 60)
    
    # Collect Tier 1: ETFs (highest priority)
    tier_1_symbols = priority_universe['tier_1_etfs']
    print(f"\n📊 Tier 1 - Index & Sector ETFs ({len(tier_1_symbols)} symbols)")
    symbols_to_update = collector.get_symbols_needing_update(tier_1_symbols)
    
    if symbols_to_update:
        result = await collector.collect_multiple_symbols_async(symbols_to_update)
        collector.update_asset_metadata(result['successful_symbols'])
    
    # Collect Tier 2: Bonds
    tier_2_symbols = priority_universe['tier_2_bonds']
    print(f"\n📊 Tier 2 - Bond ETFs ({len(tier_2_symbols)} symbols)")
    symbols_to_update = collector.get_symbols_needing_update(tier_2_symbols)
    
    if symbols_to_update:
        result = await collector.collect_multiple_symbols_async(symbols_to_update)
        collector.update_asset_metadata(result['successful_symbols'])
    
    # Collect Tier 3: Commodities
    tier_3_symbols = priority_universe['tier_3_commodities']
    print(f"\n📊 Tier 3 - Commodity ETFs ({len(tier_3_symbols)} symbols)")
    symbols_to_update = collector.get_symbols_needing_update(tier_3_symbols)
    
    if symbols_to_update:
        result = await collector.collect_multiple_symbols_async(symbols_to_update)
        collector.update_asset_metadata(result['successful_symbols'])
    
    # Summary
    summary = collector.get_collection_summary()
    print(f"\n✅ Collection Complete!")
    print(f"   📈 Total Symbols: {summary['unique_symbols']}")
    print(f"   📊 Total Records: {summary['total_records']:,}")
    print(f"\n🔝 Top Assets by Record Count:")
    print(summary['asset_summary'].head(10).to_string(index=False))

if __name__ == "__main__":
    asyncio.run(main())
