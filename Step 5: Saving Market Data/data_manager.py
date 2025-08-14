# Step 5: Saving Market Data - Enhanced Data Management System
# This module provides comprehensive data management capabilities for the Alpaca trading system

import os
import sys
import sqlite3
import pandas as pd
import pickle
import json
from datetime import datetime, timedelta
import pytz
import logging

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from Alpaca_API import ALPACA_KEY, ALPACA_SECRET

# Import alpaca data client
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_manager.log'),
        logging.StreamHandler()
    ]
)

class MarketDataManager:
    """
    Comprehensive market data management system for Step 5 requirements.
    Handles multiple storage methods, data validation, and backup strategies.
    """
    
    def __init__(self, db_path='market_data.db', backup_dir='data_backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
        self.eastern = pytz.timezone('US/Eastern')
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Initialize database
        self.initialize_database()
        
        logging.info(f"MarketDataManager initialized with database: {db_path}")
    
    def initialize_database(self):
        """Initialize SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create market_data table with enhanced schema
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
                UNIQUE(symbol, timestamp, timeframe)
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timeframe ON market_data(timeframe)')
        
        conn.commit()
        conn.close()
        
        logging.info("Database initialized with enhanced schema")
    
    def save_data_to_database(self, data_df, timeframe='Day'):
        """Save market data to SQLite database with data validation"""
        if data_df.empty:
            logging.warning("Attempted to save empty dataframe to database")
            return 0
        
        # Data validation
        required_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data_df.columns]
        if missing_columns:
            logging.error(f"Missing required columns: {missing_columns}")
            return 0
        
        # Clean and prepare data
        clean_df = self.clean_data(data_df)
        clean_df['timeframe'] = timeframe
        clean_df['data_source'] = 'Alpaca'
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Insert data with conflict resolution
            rows_inserted = clean_df.to_sql('market_data', conn, if_exists='append', 
                                          index=False)
            
            conn.close()
            
            logging.info(f"Saved {len(clean_df)} records to database (timeframe: {timeframe})")
            return len(clean_df)
            
        except Exception as e:
            logging.error(f"Error saving data to database: {e}")
            return 0
    
    def save_data_to_csv(self, data_df, filename=None):
        """Save market data to CSV files for backup and analysis"""
        if data_df.empty:
            logging.warning("Attempted to save empty dataframe to CSV")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_data_{timestamp}.csv"
        
        filepath = os.path.join(self.backup_dir, filename)
        
        try:
            data_df.to_csv(filepath, index=False)
            logging.info(f"Market data saved to CSV: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Error saving data to CSV: {e}")
            return False
    
    def save_data_to_pickle(self, data_df, filename=None):
        """Save market data to pickle files for fast loading"""
        if data_df.empty:
            logging.warning("Attempted to save empty dataframe to pickle")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_data_{timestamp}.pkl"
        
        filepath = os.path.join(self.backup_dir, filename)
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data_df, f)
            logging.info(f"Market data saved to pickle: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Error saving data to pickle: {e}")
            return False
    
    def clean_data(self, data_df):
        """Clean and validate market data"""
        clean_df = data_df.copy()
        
        # Remove rows with missing critical data
        clean_df = clean_df.dropna(subset=['open', 'high', 'low', 'close'])
        
        # Ensure proper data types
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap']
        for col in numeric_columns:
            if col in clean_df.columns:
                clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
        
        # Validate OHLC data (High >= Low, etc.)
        invalid_ohlc = (
            (clean_df['high'] < clean_df['low']) |
            (clean_df['high'] < clean_df['open']) |
            (clean_df['high'] < clean_df['close']) |
            (clean_df['low'] > clean_df['open']) |
            (clean_df['low'] > clean_df['close'])
        )
        
        if invalid_ohlc.any():
            logging.warning(f"Removing {invalid_ohlc.sum()} rows with invalid OHLC data")
            clean_df = clean_df[~invalid_ohlc]
        
        return clean_df
    
    def get_data_from_database(self, symbols=None, start_date=None, end_date=None, 
                             timeframe='Day', limit=None):
        """Retrieve market data from database with flexible filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Build query
            query = "SELECT * FROM market_data WHERE 1=1"
            params = []
            
            if symbols:
                if isinstance(symbols, str):
                    symbols = [symbols]
                placeholders = ','.join(['?' for _ in symbols])
                query += f" AND symbol IN ({placeholders})"
                params.extend(symbols)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)
            
            query += " ORDER BY symbol, timestamp"
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            logging.info(f"Retrieved {len(df)} records from database")
            return df
            
        except Exception as e:
            logging.error(f"Error retrieving data from database: {e}")
            return pd.DataFrame()
    
    def create_backup(self, backup_name=None):
        """Create a complete backup of market data in multiple formats"""
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = os.path.join(self.backup_dir, backup_name)
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        
        # Get all data from database
        all_data = self.get_data_from_database()
        
        if all_data.empty:
            logging.warning("No data found for backup")
            return False
        
        # Save in multiple formats
        success = True
        
        # CSV backup
        csv_file = os.path.join(backup_path, 'market_data.csv')
        success &= all_data.to_csv(csv_file, index=False) or True
        
        # Pickle backup
        pkl_file = os.path.join(backup_path, 'market_data.pkl')
        try:
            with open(pkl_file, 'wb') as f:
                pickle.dump(all_data, f)
        except Exception as e:
            logging.error(f"Error creating pickle backup: {e}")
            success = False
        
        # JSON backup (metadata)
        metadata = {
            'backup_date': datetime.now().isoformat(),
            'total_records': len(all_data),
            'symbols': all_data['symbol'].unique().tolist() if 'symbol' in all_data.columns else [],
            'date_range': {
                'start': all_data['timestamp'].min() if 'timestamp' in all_data.columns else None,
                'end': all_data['timestamp'].max() if 'timestamp' in all_data.columns else None
            }
        }
        
        json_file = os.path.join(backup_path, 'metadata.json')
        try:
            with open(json_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logging.error(f"Error creating JSON metadata: {e}")
            success = False
        
        if success:
            logging.info(f"Backup created successfully: {backup_path}")
        
        return success
    
    def get_data_summary(self):
        """Get summary statistics of stored data"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Basic statistics
            summary = {}
            
            # Total records
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM market_data")
            summary['total_records'] = cursor.fetchone()[0]
            
            # Symbols
            cursor.execute("SELECT DISTINCT symbol FROM market_data")
            summary['symbols'] = [row[0] for row in cursor.fetchall()]
            
            # Date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM market_data")
            date_range = cursor.fetchone()
            summary['date_range'] = {
                'start': date_range[0],
                'end': date_range[1]
            }
            
            # Records per symbol
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM market_data 
                GROUP BY symbol 
                ORDER BY count DESC
            """)
            summary['records_per_symbol'] = dict(cursor.fetchall())
            
            conn.close()
            
            logging.info("Generated data summary")
            return summary
            
        except Exception as e:
            logging.error(f"Error generating data summary: {e}")
            return {}

def main():
    """Example usage and testing of MarketDataManager"""
    # Initialize data manager
    manager = MarketDataManager()
    
    # Get summary of current data
    summary = manager.get_data_summary()
    print("\n📊 MARKET DATA SUMMARY")
    print("=" * 50)
    print(f"Total Records: {summary.get('total_records', 0)}")
    print(f"Symbols: {summary.get('symbols', [])}")
    print(f"Date Range: {summary.get('date_range', {}).get('start', 'N/A')} to {summary.get('date_range', {}).get('end', 'N/A')}")
    print(f"Records per Symbol: {summary.get('records_per_symbol', {})}")
    
    # Create backup
    print("\n💾 CREATING BACKUP")
    print("=" * 50)
    backup_success = manager.create_backup()
    if backup_success:
        print("✅ Backup created successfully")
    else:
        print("❌ Backup creation failed")
    
    # Demonstrate data retrieval
    print("\n📈 SAMPLE DATA RETRIEVAL")
    print("=" * 50)
    sample_data = manager.get_data_from_database(limit=5)
    if not sample_data.empty:
        print(sample_data.to_string())
    else:
        print("No data available")

if __name__ == "__main__":
    main()
