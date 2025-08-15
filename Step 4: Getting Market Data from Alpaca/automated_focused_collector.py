#!/usr/bin/env python3
"""
Automated Focused Data Collector for Production Use
Integrates with scheduling, monitoring, and automation systems
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
import json
import schedule
import threading
from typing import List, Dict, Optional, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_api import get_daily_bars
from step4_config import get_credentials

# Setup comprehensive logging
def setup_logging(log_level: str = 'INFO', log_file: str = 'automated_collection.log'):
    """Setup comprehensive logging for production use"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File handler with rotation
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[file_handler, console_handler]
    )
    
    return logging.getLogger(__name__)

class AutomatedFocusedCollector:
    """
    Production-ready focused data collector with automation features
    """
    
    def __init__(self, config_file: str = 'collector_config.json'):
        self.logger = setup_logging()
        self.config = self._load_config(config_file)
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
        self.eastern = pytz.timezone('US/Eastern')
        
        # Initialize components
        self._init_database()
        self.focused_assets = self._define_focused_assets()
        self.collection_stats = self._init_collection_stats()
        
        # Automation settings
        self.is_running = False
        self.scheduler_thread = None
        
        self.logger.info("AutomatedFocusedCollector initialized")
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            "collection": {
                "max_retries": 3,
                "retry_delay": 1,
                "batch_size": 5,
                "years_back": 7,
                "rate_limit_delay": 1,
                "batch_delay": 5
            },
            "scheduling": {
                "daily_update_time": "16:30",  # After market close
                "weekly_full_collection": "Sunday 18:00",
                "check_interval_minutes": 15
            },
            "monitoring": {
                "enable_email_alerts": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "email_from": "",
                "email_to": "",
                "email_password": ""
            },
            "data_quality": {
                "min_records_per_symbol": 1500,  # ~6 years of trading days
                "max_data_age_days": 2,
                "enable_validation": True
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    for key, value in user_config.items():
                        if key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
                    self.logger.info(f"Configuration loaded from {config_file}")
            else:
                # Create default config file
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                self.logger.info(f"Default configuration created: {config_file}")
        except Exception as e:
            self.logger.warning(f"Error loading config, using defaults: {e}")
        
        return default_config
    
    def _init_database(self):
        """Initialize database with proper schema and indexes"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Main data table
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
            
            # Collection tracking table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS collection_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_date TEXT NOT NULL,
                    symbols_processed INTEGER,
                    symbols_successful INTEGER,
                    symbols_failed INTEGER,
                    total_records_collected INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    status TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Data quality monitoring table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS data_quality (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    check_date TEXT NOT NULL,
                    total_records INTEGER,
                    earliest_date TEXT,
                    latest_date TEXT,
                    data_age_days INTEGER,
                    completeness_score REAL,
                    status TEXT,
                    issues TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_symbol ON market_data(symbol)',
                'CREATE INDEX IF NOT EXISTS idx_timestamp ON market_data(timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_collection_date ON collection_log(collection_date)',
                'CREATE INDEX IF NOT EXISTS idx_symbol_check_date ON data_quality(symbol, check_date)'
            ]
            
            for index in indexes:
                conn.execute(index)
            
            conn.commit()
            conn.close()
            self.logger.info("Database initialized with all tables and indexes")
            
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
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
    
    def _init_collection_stats(self) -> Dict:
        """Initialize collection statistics tracking"""
        return {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'total_records_collected': 0,
            'last_collection_date': None,
            'last_collection_status': None
        }
    
    def collect_daily_data(self, symbol: str, years_back: int = None) -> Tuple[bool, int]:
        """Collect daily data for a single symbol with enhanced error handling"""
        if years_back is None:
            years_back = self.config['collection']['years_back']
        
        for attempt in range(self.config['collection']['max_retries']):
            try:
                self.logger.info(f"Collecting daily data for {symbol} (last {years_back} years)")
                
                # Set date range
                end_date = self.eastern.localize(datetime.now())
                start_date = end_date - timedelta(days=years_back * 365)
                
                # Fetch daily bars data
                data = get_daily_bars([symbol], start_date, end_date)
                
                if data.empty:
                    self.logger.warning(f"No daily data returned for {symbol}")
                    return False, 0
                
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
                
                self.logger.info(f"✅ Successfully collected {len(data)} daily bars for {symbol}")
                return True, len(data)
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < self.config['collection']['max_retries'] - 1:
                    time.sleep(self.config['collection']['retry_delay'] * (attempt + 1))
                else:
                    self.logger.error(f"Failed to collect daily data for {symbol} after {self.config['collection']['max_retries']} attempts")
                    return False, 0
        
        return False, 0
    
    def collect_all_focused_data(self, years_back: int = None) -> Dict:
        """Collect daily data for all focused assets with comprehensive tracking"""
        if years_back is None:
            years_back = self.config['collection']['years_back']
        
        start_time = datetime.now()
        self.logger.info(f"Starting focused daily data collection for {len(self.focused_assets)} symbols (last {years_back} years)")
        
        # Initialize collection tracking
        collection_id = self._log_collection_start()
        
        # Collect data in batches
        results = {}
        total_records = 0
        
        for i in range(0, len(self.focused_assets), self.config['collection']['batch_size']):
            batch = self.focused_assets[i:i + self.config['collection']['batch_size']]
            batch_num = i // self.config['collection']['batch_size'] + 1
            total_batches = (len(self.focused_assets) + self.config['collection']['batch_size'] - 1) // self.config['collection']['batch_size']
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
            
            for symbol in batch:
                success, records = self.collect_daily_data(symbol, years_back)
                results[symbol] = success
                if success:
                    total_records += records
                
                # Rate limiting
                time.sleep(self.config['collection']['rate_limit_delay'])
            
            # Delay between batches
            if i + self.config['collection']['batch_size'] < len(self.focused_assets):
                self.logger.info(f"Waiting {self.config['collection']['batch_delay']} seconds before next batch...")
                time.sleep(self.config['collection']['batch_delay'])
        
        # Finalize collection tracking
        end_time = datetime.now()
        successful = sum(results.values())
        failed = len(results) - successful
        
        self._log_collection_end(collection_id, len(results), successful, failed, total_records, start_time, end_time, 'SUCCESS')
        
        # Update stats
        self.collection_stats['total_collections'] += 1
        self.collection_stats['successful_collections'] += 1
        self.collection_stats['total_records_collected'] += total_records
        self.collection_stats['last_collection_date'] = datetime.now().isoformat()
        self.collection_stats['last_collection_status'] = 'SUCCESS'
        
        self.logger.info(f"Focused daily data collection complete: {successful}/{len(results)} symbols successful, {total_records:,} total records")
        
        return {
            'total_symbols': len(results),
            'successful_symbols': successful,
            'failed_symbols': failed,
            'total_records': total_records,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_minutes': (end_time - start_time).total_seconds() / 60
        }
    
    def _log_collection_start(self) -> int:
        """Log the start of a collection run"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('''
                INSERT INTO collection_log 
                (collection_date, symbols_processed, symbols_successful, symbols_failed, 
                 total_records_collected, start_time, status)
                VALUES (?, 0, 0, 0, 0, ?, 'RUNNING')
            ''', (datetime.now().date().isoformat(), datetime.now().isoformat()))
            
            collection_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return collection_id
        except Exception as e:
            self.logger.error(f"Error logging collection start: {e}")
            return 0
    
    def _log_collection_end(self, collection_id: int, processed: int, successful: int, 
                           failed: int, records: int, start_time: datetime, 
                           end_time: datetime, status: str, error_msg: str = None):
        """Log the end of a collection run"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                UPDATE collection_log 
                SET symbols_processed = ?, symbols_successful = ?, symbols_failed = ?,
                    total_records_collected = ?, end_time = ?, status = ?, error_message = ?
                WHERE id = ?
            ''', (processed, successful, failed, records, end_time.isoformat(), status, error_msg, collection_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error logging collection end: {e}")
    
    def incremental_update(self) -> Dict:
        """Perform incremental update of recent data"""
        self.logger.info("Starting incremental data update")
        
        # Get symbols that need updates
        symbols_to_update = self._get_symbols_needing_update()
        
        if not symbols_to_update:
            self.logger.info("No symbols need updates")
            return {'status': 'no_updates_needed', 'symbols_updated': 0}
        
        self.logger.info(f"Updating {len(symbols_to_update)} symbols")
        
        # Update each symbol with recent data
        results = {}
        total_records = 0
        
        for symbol in symbols_to_update:
            success, records = self.collect_daily_data(symbol, years_back=1)  # Last year only
            results[symbol] = success
            if success:
                total_records += records
            
            time.sleep(self.config['collection']['rate_limit_delay'])
        
        successful = sum(results.values())
        self.logger.info(f"Incremental update complete: {successful}/{len(results)} symbols updated")
        
        return {
            'status': 'success',
            'symbols_updated': len(results),
            'successful_updates': successful,
            'total_records': total_records
        }
    
    def _get_symbols_needing_update(self) -> List[str]:
        """Get symbols that need data updates"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check which symbols need updates (data older than max_data_age_days)
            cutoff_date = (datetime.now() - timedelta(days=self.config['data_quality']['max_data_age_days'])).date()
            
            query = """
                SELECT DISTINCT symbol 
                FROM market_data 
                WHERE DATE(MAX(timestamp)) < ?
                GROUP BY symbol
            """
            
            results = conn.execute(query, (cutoff_date.isoformat(),)).fetchall()
            conn.close()
            
            return [row[0] for row in results]
            
        except Exception as e:
            self.logger.error(f"Error getting symbols needing update: {e}")
            return []
    
    def check_data_quality(self) -> Dict:
        """Check data quality for all symbols"""
        self.logger.info("Starting data quality check")
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            quality_results = {}
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

                    if latest.tzinfo is None:
                        latest = latest.tz_localize('UTC')
                    else:
                        latest = latest.tz_convert('UTC')

                    days_span = (latest - earliest).days
                    data_age_days = (pd.Timestamp.now(tz='UTC') - latest).days
                    
                    # Calculate completeness score
                    expected_days = 365 * self.config['collection']['years_back']
                    completeness_score = min(1.0, days_span / expected_days)
                    
                    # Determine status
                    if data_age_days <= self.config['data_quality']['max_data_age_days']:
                        status = 'CURRENT'
                    elif completeness_score >= 0.8:
                        status = 'GOOD'
                    elif completeness_score >= 0.6:
                        status = 'FAIR'
                    else:
                        status = 'POOR'
                    
                    # Check for issues
                    issues = []
                    if data_age_days > self.config['data_quality']['max_data_age_days']:
                        issues.append(f"Data {data_age_days} days old")
                    if result[0] < self.config['data_quality']['min_records_per_symbol']:
                        issues.append(f"Only {result[0]} records")
                    
                    quality_results[symbol] = {
                        'records': result[0],
                        'earliest_date': result[1],
                        'latest_date': result[2],
                        'days_span': days_span,
                        'data_age_days': data_age_days,
                        'completeness_score': completeness_score,
                        'status': status,
                        'issues': '; '.join(issues) if issues else 'None'
                    }
                    
                    # Log to database
                    self._log_data_quality(symbol, quality_results[symbol])
                else:
                    quality_results[symbol] = {
                        'records': 0,
                        'earliest_date': None,
                        'latest_date': None,
                        'days_span': 0,
                        'data_age_days': None,
                        'completeness_score': 0.0,
                        'status': 'MISSING',
                        'issues': 'No data found'
                    }
            
            conn.close()
            
            # Summary statistics
            status_counts = {}
            for result in quality_results.values():
                status = result['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            self.logger.info(f"Data quality check complete: {status_counts}")
            
            return {
                'total_symbols': len(quality_results),
                'status_counts': status_counts,
                'symbol_details': quality_results
            }
            
        except Exception as e:
            self.logger.error(f"Error checking data quality: {e}")
            return {'error': str(e)}
    
    def _log_data_quality(self, symbol: str, quality_data: Dict):
        """Log data quality check results to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT OR REPLACE INTO data_quality 
                (symbol, check_date, total_records, earliest_date, latest_date, 
                 data_age_days, completeness_score, status, issues)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, datetime.now().date().isoformat(), quality_data['records'],
                quality_data['earliest_date'], quality_data['latest_date'],
                quality_data['data_age_days'], quality_data['completeness_score'],
                quality_data['status'], quality_data['issues']
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error logging data quality for {symbol}: {e}")
    
    def setup_scheduling(self):
        """Setup automated scheduling for data collection"""
        if self.is_running:
            self.logger.warning("Scheduler already running")
            return
        
        # Daily incremental updates
        schedule.every().day.at(self.config['scheduling']['daily_update_time']).do(self.incremental_update)
        
        # Weekly full collection
        schedule.every().sunday.at(self.config['scheduling']['weekly_full_collection']).do(self.collect_all_focused_data)
        
        # Data quality checks
        schedule.every().day.at("09:00").do(self.check_data_quality)
        
        self.logger.info("Scheduling setup complete")
        self.logger.info(f"Daily updates: {self.config['scheduling']['daily_update_time']}")
        self.logger.info(f"Weekly full collection: {self.config['scheduling']['weekly_full_collection']}")
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        if self.is_running:
            self.logger.warning("Scheduler already running")
            return
        
        self.setup_scheduling()
        self.is_running = True
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(self.config['scheduling']['check_interval_minutes'] * 60)
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("Automated scheduler started")
    
    def stop_scheduler(self):
        """Stop the automated scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Automated scheduler stopped")
    
    def send_email_alert(self, subject: str, message: str):
        """Send email alert if configured"""
        if not self.config['monitoring']['enable_email_alerts']:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['monitoring']['email_from']
            msg['To'] = self.config['monitoring']['email_to']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.config['monitoring']['smtp_server'], self.config['monitoring']['smtp_port'])
            server.starttls()
            server.login(self.config['monitoring']['email_from'], self.config['monitoring']['email_password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Email alert sent successfully")
        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")
    
    def get_collection_history(self, days_back: int = 30) -> List[Dict]:
        """Get collection history for monitoring"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
                SELECT * FROM collection_log 
                WHERE DATE(created_at) >= DATE('now', '-{} days')
                ORDER BY created_at DESC
            ""..
            
            results = pd.read_sql_query(query, conn)
            conn.close()
            
            return results.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"Error getting collection history: {e}")
            return []
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        try:
            # Database status
            conn = sqlite3.connect(self.db_path)
            total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM market_data").fetchone()[0]
            total_records = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
            
            # Latest collection status
            latest_collection = conn.execute("""
                SELECT * FROM collection_log 
                ORDER BY created_at DESC 
                LIMIT 1
            """ ).fetchone()
            
            conn.close()
            
            # Data quality summary
            quality_summary = self.check_data_quality()
            
            return {
                'database': {
                    'total_symbols': total_symbols,
                    'total_records': total_records,
                    'db_size_mb': os.path.getsize(self.db_path) / (1024 * 1024)
                },
                'scheduler': {
                    'is_running': self.is_running,
                    'next_run': schedule.next_run() if schedule.jobs else None
                },
                'latest_collection': {
                    'date': latest_collection[1] if latest_collection else None,
                    'status': latest_collection[7] if latest_collection else None,
                    'symbols_processed': latest_collection[2] if latest_collection else 0
                },
                'data_quality': quality_summary.get('status_counts', {}),
                'collection_stats': self.collection_stats
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}

def main():
    """Main function for automated focused data collection"""
    print("🚀 AUTOMATED FOCUSED DATA COLLECTOR")
    print("=" * 70)
    print("Production-ready data collection with automation, scheduling, and monitoring")
    print("=" * 70)
    
    collector = AutomatedFocusedCollector()
    
    # Show system status
    print(f"\n📊 SYSTEM STATUS:")
    status = collector.get_system_status()
    if 'error' not in status:
        print(f"   Database: {status['database']['total_symbols']} symbols, {status['database']['total_records']:,} records")
        print(f"   Scheduler: {'Running' if status['scheduler']['is_running'] else 'Stopped'}")
        print(f"   Latest Collection: {status['latest_collection']['status']}")
    else:
        print("   Status: Error retrieving system status")
    
    print(f"\n📋 FOCUSED ASSET UNIVERSE:")
    print(f"   Total Assets: {len(collector.focused_assets)}")
    print(f"   Categories: Core ETFs, Sector ETFs, Tech Giants, Financial Leaders,")
    print(f"               Healthcare, Consumer, Energy, International, Leveraged")
    
    print(f"\n🎯 OPTIONS:")
    print("   1. Collect full daily data (7+ years)")
    print("   2. Perform incremental update")
    print("   3. Check data quality")
    print("   4. Start automated scheduler")
    print("   5. Stop automated scheduler")
    print("   6. View collection history")
    print("   7. View system status")
    print("   8. Exit")
    
    choice = input("\nEnter your choice (1-8): ").strip()
    
    if choice == '1':
        print(f"\n📥 Collecting full daily data (7+ years)...")
        results = collector.collect_all_focused_data()
        print(f"✅ Collection complete: {results['successful_symbols']}/{results['total_symbols']} symbols successful")
        print(f"   Total records: {results['total_records']:,}")
        print(f"   Duration: {results['duration_minutes']:.1f} minutes")
        
    elif choice == '2':
        print(f"\n🔄 Performing incremental update...")
        results = collector.incremental_update()
        print(f"✅ Update complete: {results['status']}")
        if 'symbols_updated' in results:
            print(f"   Symbols updated: {results['symbols_updated']}")
        
    elif choice == '3':
        print(f"\n🔍 Checking data quality...")
        quality = collector.check_data_quality()
        if 'error' not in quality:
            print(f"✅ Quality check complete:")
            for status, count in quality['status_counts'].items():
                print(f"   {status}: {count} symbols")
        else:
            print(f"❌ Error: {quality['error']}")
        
    elif choice == '4':
        print(f"\n🚀 Starting automated scheduler...")
        collector.start_scheduler()
        print(f"✅ Scheduler started successfully")
        
    elif choice == '5':
        print(f"\n⏹️  Stopping automated scheduler...")
        collector.stop_scheduler()
        print(f"✅ Scheduler stopped successfully")
        
    elif choice == '6':
        print(f"\n📚 Collection history (last 30 days):")
        history = collector.get_collection_history()
        if history:
            for entry in history[:5]:  # Show last 5 entries
                print(f"   {entry['collection_date']}: {entry['symbols_successful']}/{entry['symbols_processed']} successful")
        else:
            print("   No collection history found")
        
    elif choice == '7':
        print(f"\n📊 System status:")
        status = collector.get_system_status()
        if 'error' not in status:
            print(f"   Database: {status['database']['total_symbols']} symbols")
            print(f"   Total Records: {status['database']['total_records']:,}")
            print(f"   DB Size: {status['database']['db_size_mb']:.1f} MB")
            print(f"   Scheduler: {'Running' if status['scheduler']['is_running'] else 'Stopped'}")
            print(f"   Latest Collection: {status['latest_collection']['status']}")
            print(f"   Data Quality: {status['data_quality']}")
        else:
            print(f"❌ Error: {status['error']}")
        
    elif choice == '8':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")
    
    print(f"\n💡 NEXT STEPS:")
    print("   1. Use this data for your 14-day RSI strategy")
    print("   2. Test strategy with trading_strategy.py")
    print("   3. Set up automated scheduling for continuous updates")
    print("   4. Monitor data quality and system performance")

if __name__ == "__main__":
    main()
