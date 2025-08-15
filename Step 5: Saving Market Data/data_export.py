# Step 5: Data Export Utility
# Multiple format export system for backtesting and analysis

import os
import sys
import pandas as pd
import json
import csv
from datetime import datetime
import argparse
import logging

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from data_manager import MarketDataManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataExporter:
    """
    Utility to export market data in various formats for backtesting and analysis
    """
    
    def __init__(self):
        self.data_manager = MarketDataManager()
        self.export_dir = 'exports'
        
        # Create export directory
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
        
        logging.info("DataExporter initialized")
    
    def export_to_csv(self, symbols=None, start_date=None, end_date=None, 
                     filename=None, separate_files=False):
        """Export data to CSV format"""
        data = self.data_manager.get_data_from_database(
            symbols=symbols, start_date=start_date, end_date=end_date
        )
        
        if data.empty:
            logging.warning("No data found for export")
            return False
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if separate_files and 'symbol' in data.columns:
            # Export separate CSV for each symbol
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol]
                symbol_filename = f"{symbol}_data_{timestamp}.csv"
                filepath = os.path.join(self.export_dir, symbol_filename)
                symbol_data.to_csv(filepath, index=False)
                logging.info(f"Exported {symbol} data to {filepath}")
        else:
            # Single CSV file
            if filename is None:
                filename = f"market_data_export_{timestamp}.csv"
            filepath = os.path.join(self.export_dir, filename)
            data.to_csv(filepath, index=False)
            logging.info(f"Exported data to {filepath}")
        
        return True
    
    def export_to_json(self, symbols=None, start_date=None, end_date=None, filename=None):
        """Export data to JSON format"""
        data = self.data_manager.get_data_from_database(
            symbols=symbols, start_date=start_date, end_date=end_date
        )
        
        if data.empty:
            logging.warning("No data found for export")
            return False
        
        # Convert to JSON-friendly format
        data_dict = data.to_dict('records')
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_data_export_{timestamp}.json"
        
        filepath = os.path.join(self.export_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data_dict, f, indent=2, default=str)
        
        logging.info(f"Exported data to {filepath}")
        return True
    
    def export_for_backtesting(self, symbols=None, start_date=None, end_date=None):
        """Export data in formats commonly used for backtesting"""
        data = self.data_manager.get_data_from_database(
            symbols=symbols, start_date=start_date, end_date=end_date
        )
        
        if data.empty:
            logging.warning("No data found for backtesting export")
            return False
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backtesting directory
        backtest_dir = os.path.join(self.export_dir, f'backtesting_{timestamp}')
        os.makedirs(backtest_dir, exist_ok=True)
        
        if 'symbol' in data.columns:
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol].copy()
                
                # Ensure proper datetime index for backtesting
                if 'timestamp' in symbol_data.columns:
                    symbol_data['timestamp'] = pd.to_datetime(symbol_data['timestamp'])
                    symbol_data.set_index('timestamp', inplace=True)
                
                # Select only OHLCV columns for backtesting
                backtest_columns = ['open', 'high', 'low', 'close', 'volume']
                available_columns = [col for col in backtest_columns if col in symbol_data.columns]
                symbol_data = symbol_data[available_columns]
                
                # Export in multiple formats
                csv_file = os.path.join(backtest_dir, f'{symbol}_ohlcv.csv')
                symbol_data.to_csv(csv_file)
                
                pkl_file = os.path.join(backtest_dir, f'{symbol}_ohlcv.pkl')
                symbol_data.to_pickle(pkl_file)
                
                logging.info(f"Exported {symbol} backtesting data")
        
        # Create metadata file
        metadata = {
            'export_date': datetime.now().isoformat(),
            'symbols': symbols or data['symbol'].unique().tolist() if 'symbol' in data.columns else [],
            'date_range': {
                'start': start_date or data['timestamp'].min() if 'timestamp' in data.columns else None,
                'end': end_date or data['timestamp'].max() if 'timestamp' in data.columns else None
            },
            'total_records': len(data),
            'format': 'OHLCV for backtesting'
        }
        
        metadata_file = os.path.join(backtest_dir, 'metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logging.info(f"Backtesting export completed: {backtest_dir}")
        return True
    
    def export_summary_report(self, filename=None):
        """Export a comprehensive summary report"""
        summary = self.data_manager.get_data_summary()
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data_summary_report_{timestamp}.json"
        
        filepath = os.path.join(self.export_dir, filename)
        
        # Enhanced summary with additional statistics
        enhanced_summary = {
            **summary,
            'export_date': datetime.now().isoformat(),
            'database_path': self.data_manager.db_path,
            'export_formats_available': ['CSV', 'JSON', 'Pickle', 'Backtesting'],
        }
        
        with open(filepath, 'w') as f:
            json.dump(enhanced_summary, f, indent=2, default=str)
        
        logging.info(f"Summary report exported: {filepath}")
        return True

def main():
    """Command-line interface for data export utility"""
    parser = argparse.ArgumentParser(description='Export market data in various formats')
    parser.add_argument('--format', choices=['csv', 'json', 'backtest', 'summary'], 
                       default='csv', help='Export format')
    parser.add_argument('--symbols', nargs='+', help='Symbols to export (e.g., SPY VXX)')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--filename', help='Custom filename')
    parser.add_argument('--separate', action='store_true', 
                       help='Create separate files for each symbol')
    
    args = parser.parse_args()
    
    exporter = DataExporter()
    
    print("📤 DATA EXPORT UTILITY")
    print("=" * 50)
    print(f"Format: {args.format}")
    print(f"Symbols: {args.symbols or 'All'}")
    print(f"Date range: {args.start_date or 'All'} to {args.end_date or 'All'}")
    print()
    
    success = False
    
    if args.format == 'csv':
        success = exporter.export_to_csv(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            filename=args.filename,
            separate_files=args.separate
        )
    elif args.format == 'json':
        success = exporter.export_to_json(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            filename=args.filename
        )
    elif args.format == 'backtest':
        success = exporter.export_for_backtesting(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date
        )
    elif args.format == 'summary':
        success = exporter.export_summary_report(filename=args.filename)
    
    if success:
        print("✅ Export completed successfully")
    else:
        print("❌ Export failed")

if __name__ == "__main__":
    main()
