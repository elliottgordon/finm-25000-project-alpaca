# Step 5: Database Migration Script
# Migrate Step 4 database to Step 5 enhanced schema

import sqlite3
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def migrate_database(db_path='market_data.db'):
    """
    Migrate existing Step 4 database to Step 5 enhanced schema
    """
    logging.info(f"Starting database migration for: {db_path}")
    
    if not os.path.exists(db_path):
        logging.error(f"Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(market_data)")
        columns = [row[1] for row in cursor.fetchall()]
        logging.info(f"Current columns: {columns}")
        
        # Add missing columns if they don't exist
        new_columns = {
            'timeframe': 'TEXT DEFAULT "Day"',
            'data_source': 'TEXT DEFAULT "Alpaca"',
            'created_at': 'TEXT'  # Remove default for SQLite compatibility
        }
        
        for column_name, column_def in new_columns.items():
            if column_name not in columns:
                try:
                    cursor.execute(f'ALTER TABLE market_data ADD COLUMN {column_name} {column_def}')
                    logging.info(f"Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    logging.warning(f"Could not add column {column_name}: {e}")
        
        # Update existing records with default values
        cursor.execute("""
            UPDATE market_data 
            SET timeframe = COALESCE(timeframe, 'Day'), 
                data_source = COALESCE(data_source, 'Alpaca'), 
                created_at = COALESCE(created_at, datetime('now'))
        """)
        
        # Create indexes if they don't exist
        indexes = [
            ('idx_symbol_timestamp', 'symbol, timestamp'),
            ('idx_timeframe', 'timeframe')
        ]
        
        for index_name, index_columns in indexes:
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON market_data({index_columns})')
                logging.info(f"Created index: {index_name}")
            except sqlite3.OperationalError as e:
                logging.warning(f"Could not create index {index_name}: {e}")
        
        # Add unique constraint if it doesn't exist (create new table and migrate)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_data_new'")
        if not cursor.fetchone():
            # Create new table with proper constraints
            cursor.execute('''
                CREATE TABLE market_data_new (
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
            
            # Copy data from old table to new table
            cursor.execute('''
                INSERT OR IGNORE INTO market_data_new 
                (symbol, timestamp, open, high, low, close, volume, trade_count, vwap, timeframe, data_source, created_at)
                SELECT symbol, timestamp, open, high, low, close, volume, trade_count, vwap, 
                       COALESCE(timeframe, 'Day'), 
                       COALESCE(data_source, 'Alpaca'),
                       COALESCE(created_at, datetime('now'))
                FROM market_data
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE market_data')
            cursor.execute('ALTER TABLE market_data_new RENAME TO market_data')
            
            # Recreate indexes on new table
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timeframe ON market_data(timeframe)')
            
            logging.info("Database schema migration completed")
        
        conn.commit()
        conn.close()
        
        logging.info("Database migration successful")
        return True
        
    except Exception as e:
        logging.error(f"Database migration failed: {e}")
        return False

def main():
    """Run database migration"""
    print("🔄 DATABASE MIGRATION - Step 4 to Step 5")
    print("=" * 50)
    
    success = migrate_database('market_data.db')
    
    if success:
        print("✅ Migration completed successfully")
        
        # Test the migrated database
        conn = sqlite3.connect('market_data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM market_data")
        record_count = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA table_info(market_data)")
        columns = [row[1] for row in cursor.fetchall()]
        
        conn.close()
        
        print(f"📊 Records preserved: {record_count}")
        print(f"🗂️  New schema columns: {columns}")
        
    else:
        print("❌ Migration failed")

if __name__ == "__main__":
    main()
