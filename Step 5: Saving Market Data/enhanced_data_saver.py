# Step 5: Integration with Step 4 Data Pipeline
# Enhanced data_saver that integrates with the comprehensive data management system

import os
import sys
import sqlite3
import pandas as pd
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

# Import our data management system
from data_manager import MarketDataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_data_saver.log'),
        logging.StreamHandler()
    ]
)

class EnhancedDataSaver:
    """
    Enhanced version of data_saver.py that integrates with Step 5 data management system
    Provides comprehensive data collection, validation, and storage capabilities
    """
    
    def __init__(self):
        self.client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
        self.data_manager = MarketDataManager()
        self.eastern = pytz.timezone('US/Eastern')
        
        # Configuration
        self.symbols = ["SPY", "VXX"]
        self.timeframe = TimeFrame.Day
        
        # Historical data collection settings (7 years as tested)
        self.start_date = self.eastern.localize(datetime(2018, 1, 1))
        self.end_date = self.eastern.localize(datetime.now() - timedelta(days=1))
        
        logging.info("EnhancedDataSaver initialized with Step 5 data management")
    
    def get_historical_data(self, symbols, start, end, timeframe=TimeFrame.Day):
        """
        Get historical data from Alpaca API with enhanced error handling and validation
        """
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=timeframe,
                start=start,
                end=end,
                adjustment=Adjustment.RAW
            )
            
            logging.info(f"Fetching historical data for {symbols} from {start} to {end}")
            
            # Get data from Alpaca
            bars = self.client.get_stock_bars(request_params).df.reset_index()
            
            if not bars.empty:
                logging.info(f"Successfully retrieved {len(bars)} records")
                
                # Validate data quality using our data manager
                clean_bars = self.data_manager.clean_data(bars)
                
                if len(clean_bars) != len(bars):
                    logging.warning(f"Data cleaning removed {len(bars) - len(clean_bars)} invalid records")
                
                return clean_bars
            else:
                logging.warning("No data returned from Alpaca API")
                return pd.DataFrame()
                
        except Exception as e:
            logging.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def save_data_comprehensive(self, data_df, create_backup=True):
        """
        Save data using comprehensive Step 5 data management system
        """
        if data_df.empty:
            logging.warning("No data to save")
            return 0
        
        # Save to database
        records_saved = self.data_manager.save_data_to_database(data_df, timeframe='Day')
        
        if records_saved > 0:
            logging.info(f"Saved {records_saved} records to database")
            
            # Create backup files if requested
            if create_backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Save CSV backup
                self.data_manager.save_data_to_csv(data_df, f"historical_data_{timestamp}.csv")
                
                # Save pickle backup for fast loading
                self.data_manager.save_data_to_pickle(data_df, f"historical_data_{timestamp}.pkl")
        
        return records_saved
    
    def get_latest_timestamp_enhanced(self):
        """
        Get latest timestamp using enhanced data management system
        """
        try:
            # Get latest data for our symbols
            latest_data = self.data_manager.get_data_from_database(
                symbols=self.symbols, limit=1
            )
            
            if not latest_data.empty and 'timestamp' in latest_data.columns:
                latest_timestamp_str = latest_data['timestamp'].iloc[-1]
                latest_timestamp = datetime.fromisoformat(latest_timestamp_str.replace(' ', 'T'))
                
                # Make timezone-aware if needed
                if latest_timestamp.tzinfo is None:
                    latest_timestamp = self.eastern.localize(latest_timestamp)
                
                logging.info(f"Latest timestamp in database: {latest_timestamp}")
                return latest_timestamp
            else:
                logging.info("No existing data found in database")
                return None
                
        except Exception as e:
            logging.error(f"Error getting latest timestamp: {e}")
            return None
    
    def run_initial_data_collection(self):
        """
        Run initial 7-year historical data collection
        """
        logging.info("Starting initial 7-year historical data collection")
        
        # Check if we already have data
        existing_summary = self.data_manager.get_data_summary()
        
        if existing_summary.get('total_records', 0) > 0:
            logging.info(f"Found {existing_summary['total_records']} existing records")
            logging.info("Checking for data gaps...")
            
            latest_timestamp = self.get_latest_timestamp_enhanced()
            if latest_timestamp and latest_timestamp < self.end_date:
                # Update with recent data
                start_update = latest_timestamp + timedelta(days=1)
                logging.info(f"Updating data from {start_update} to {self.end_date}")
                
                new_data = self.get_historical_data(self.symbols, start_update, self.end_date)
                if not new_data.empty:
                    self.save_data_comprehensive(new_data)
            else:
                logging.info("Database is up to date")
        else:
            # Initial full collection
            logging.info("No existing data found. Starting full 7-year collection...")
            
            historical_data = self.get_historical_data(
                self.symbols, self.start_date, self.end_date, self.timeframe
            )
            
            if not historical_data.empty:
                records_saved = self.save_data_comprehensive(historical_data)
                logging.info(f"Initial collection complete: {records_saved} records saved")
            else:
                logging.error("Failed to collect initial historical data")
    
    def run_incremental_update(self):
        """
        Run incremental update for new data (called by scheduler)
        """
        logging.info("Running incremental data update")
        
        latest_timestamp = self.get_latest_timestamp_enhanced()
        
        if latest_timestamp:
            # Get data from day after latest to yesterday
            update_start = latest_timestamp + timedelta(days=1)
            update_end = self.eastern.localize(datetime.now() - timedelta(days=1))
            
            if update_start < update_end:
                logging.info(f"Updating data from {update_start} to {update_end}")
                
                new_data = self.get_historical_data(self.symbols, update_start, update_end)
                
                if not new_data.empty:
                    records_saved = self.save_data_comprehensive(new_data)
                    logging.info(f"Incremental update complete: {records_saved} new records")
                else:
                    logging.info("No new data available")
            else:
                logging.info("Database is already up to date")
        else:
            logging.warning("Could not determine latest timestamp, running initial collection")
            self.run_initial_data_collection()
    
    def generate_status_report(self):
        """
        Generate comprehensive status report
        """
        summary = self.data_manager.get_data_summary()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'operational',
            'data_summary': summary,
            'configuration': {
                'symbols': self.symbols,
                'timeframe': 'Daily',
                'historical_range': f"{self.start_date.date()} to {self.end_date.date()}",
                'database_path': self.data_manager.db_path
            },
            'data_quality': {
                'has_data': summary.get('total_records', 0) > 0,
                'symbols_covered': len(summary.get('symbols', [])),
                'date_coverage': summary.get('date_range', {})
            }
        }
        
        return report

def main():
    """
    Main execution function for enhanced data saver
    """
    print("🚀 ENHANCED DATA SAVER (Step 5 Integration)")
    print("=" * 60)
    
    # Initialize enhanced data saver
    saver = EnhancedDataSaver()
    
    # Run initial data collection
    saver.run_initial_data_collection()
    
    # Generate status report
    report = saver.generate_status_report()
    print("\n📊 STATUS REPORT")
    print("-" * 30)
    print(f"Total Records: {report['data_summary'].get('total_records', 0)}")
    print(f"Symbols: {report['data_summary'].get('symbols', [])}")
    print(f"Date Range: {report['data_summary'].get('date_range', {})}")
    print(f"Database: {report['configuration']['database_path']}")
    
    print("\n✅ Enhanced data collection completed")

if __name__ == "__main__":
    main()
