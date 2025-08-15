# Step 5: Complete Data Workflow Pipeline
# Demonstrates the full data management, export, and analysis workflow

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import argparse

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from data_management import MarketDataManager
from data_export import DataExporter
from data_analyzer import MarketDataAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_workflow.log'),
        logging.StreamHandler()
    ]
)

class DataWorkflow:
    """
    Complete data workflow pipeline for Step 5 requirements.
    Integrates data management, export, and analysis in a single workflow.
    """
    
    def __init__(self):
        self.data_manager = MarketDataManager()
        self.data_exporter = DataExporter()
        self.data_analyzer = MarketDataAnalyzer()
        
        logging.info("DataWorkflow initialized")
    
    def run_complete_workflow(self, symbols, start_date=None, end_date=None, 
                            export_formats=['csv', 'json'], create_analysis=True):
        """
        Run complete data workflow: management -> export -> analysis
        """
        print("🚀 COMPLETE DATA WORKFLOW PIPELINE")
        print("=" * 60)
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Date Range: {start_date or 'All'} to {end_date or 'All'}")
        print(f"Export Formats: {', '.join(export_formats)}")
        print(f"Create Analysis: {create_analysis}")
        print()
        
        workflow_results = {
            'workflow_date': datetime.now().isoformat(),
            'symbols': symbols,
            'date_range': {'start': start_date, 'end': end_date},
            'steps_completed': [],
            'exports_created': [],
            'analysis_results': None
        }
        
        # Step 1: Data Management and Validation
        print("📊 STEP 1: DATA MANAGEMENT & VALIDATION")
        print("-" * 40)
        
        # Get data summary
        summary = self.data_manager.get_data_summary()
        print(f"✅ Database contains {summary.get('total_records', 0)} total records")
        print(f"✅ Available symbols: {len(summary.get('symbols', []))}")
        
        # Validate data availability for requested symbols
        available_symbols = []
        for symbol in symbols:
            data = self.data_manager.get_data_from_database(symbols=symbol, start_date=start_date, end_date=end_date)
            if not data.empty:
                available_symbols.append(symbol)
                print(f"✅ {symbol}: {len(data)} records available")
            else:
                print(f"⚠️  {symbol}: No data available for specified date range")
        
        if not available_symbols:
            print("❌ No data available for any requested symbols")
            return workflow_results
        
        workflow_results['steps_completed'].append('data_validation')
        workflow_results['available_symbols'] = available_symbols
        
        # Step 2: Data Export
        print(f"\n📤 STEP 2: DATA EXPORT")
        print("-" * 40)
        
        exports_created = []
        
        for export_format in export_formats:
            try:
                if export_format == 'csv':
                    success = self.data_exporter.export_to_csv(
                        symbols=available_symbols,
                        start_date=start_date,
                        end_date=end_date,
                        separate_files=True
                    )
                    if success:
                        exports_created.append('csv_separate')
                        print("✅ CSV export completed (separate files per symbol)")
                
                elif export_format == 'json':
                    success = self.data_exporter.export_to_json(
                        symbols=available_symbols,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if success:
                        exports_created.append('json')
                        print("✅ JSON export completed")
                
                elif export_format == 'backtest':
                    success = self.data_exporter.export_for_backtesting(
                        symbols=available_symbols,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if success:
                        exports_created.append('backtest')
                        print("✅ Backtesting export completed")
                
            except Exception as e:
                logging.error(f"Export failed for format {export_format}: {e}")
                print(f"❌ Export failed for {export_format}: {e}")
        
        workflow_results['steps_completed'].append('data_export')
        workflow_results['exports_created'] = exports_created
        
        # Step 3: Data Analysis
        if create_analysis:
            print(f"\n📈 STEP 3: DATA ANALYSIS")
            print("-" * 40)
            
            try:
                # Create individual symbol charts
                for symbol in available_symbols[:3]:  # Limit to first 3 for performance
                    print(f"📊 Creating analysis chart for {symbol}...")
                    self.data_analyzer.create_price_chart(symbol, start_date=start_date, end_date=end_date)
                
                # Create correlation matrix if multiple symbols
                if len(available_symbols) > 1:
                    print(f"🔗 Creating correlation matrix...")
                    correlation_matrix = self.data_analyzer.create_correlation_matrix(
                        available_symbols, start_date=start_date, end_date=end_date
                    )
                
                # Portfolio analysis
                if len(available_symbols) > 1:
                    print(f"💼 Creating portfolio analysis...")
                    portfolio_stats = self.data_analyzer.create_portfolio_analysis(
                        available_symbols, start_date=start_date, end_date=end_date
                    )
                    
                    if portfolio_stats:
                        print(f"  Portfolio Return: {portfolio_stats['total_return']:.2%}")
                        print(f"  Volatility: {portfolio_stats['volatility']:.2%}")
                        print(f"  Sharpe Ratio: {portfolio_stats['sharpe_ratio']:.2f}")
                
                # Generate comprehensive report
                print(f"📋 Generating analysis report...")
                analysis_report = self.data_analyzer.generate_analysis_report(
                    available_symbols, start_date=start_date, end_date=end_date
                )
                
                workflow_results['analysis_results'] = analysis_report
                workflow_results['steps_completed'].append('data_analysis')
                print("✅ Data analysis completed")
                
            except Exception as e:
                logging.error(f"Data analysis failed: {e}")
                print(f"❌ Data analysis failed: {e}")
        
        # Step 4: Create Backup
        print(f"\n💾 STEP 4: CREATE BACKUP")
        print("-" * 40)
        
        try:
            backup_success = self.data_manager.create_backup()
            if backup_success:
                workflow_results['steps_completed'].append('backup_creation')
                print("✅ Backup created successfully")
            else:
                print("❌ Backup creation failed")
        except Exception as e:
            logging.error(f"Backup creation failed: {e}")
            print(f"❌ Backup creation failed: {e}")
        
        # Workflow Summary
        print(f"\n🎯 WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"✅ Steps Completed: {len(workflow_results['steps_completed'])}")
        print(f"✅ Exports Created: {len(workflow_results['exports_created'])}")
        print(f"✅ Analysis: {'Completed' if create_analysis else 'Skipped'}")
        print(f"✅ Backup: {'Created' if 'backup_creation' in workflow_results['steps_completed'] else 'Failed'}")
        
        return workflow_results
    
    def quick_data_overview(self, symbols=None, limit=5):
        """Quick overview of available data"""
        print("🔍 QUICK DATA OVERVIEW")
        print("=" * 40)
        
        # Get overall summary
        summary = self.data_manager.get_data_summary()
        print(f"Total Records: {summary.get('total_records', 0):,}")
        print(f"Total Symbols: {len(summary.get('symbols', []))}")
        print(f"Date Range: {summary.get('date_range', {}).get('start', 'N/A')} to {summary.get('date_range', {}).get('end', 'N/A')}")
        
        # Show top symbols by record count
        records_per_symbol = summary.get('records_per_symbol', {})
        if records_per_symbol:
            top_symbols = sorted(records_per_symbol.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f"\nTop 10 Symbols by Record Count:")
            for symbol, count in top_symbols:
                print(f"  {symbol}: {count:,} records")
        
        # Show sample data
        if symbols:
            print(f"\nSample Data for {', '.join(symbols)}:")
            for symbol in symbols[:3]:  # Limit to first 3
                data = self.data_manager.get_data_from_database(symbols=symbol, limit=limit)
                if not data.empty:
                    print(f"\n{symbol} (showing {len(data)} records):")
                    print(data[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))
                else:
                    print(f"{symbol}: No data available")
    
    def data_quality_check(self, symbols=None):
        """Check data quality and identify potential issues"""
        print("🔍 DATA QUALITY CHECK")
        print("=" * 40)
        
        if symbols is None:
            # Get top symbols by record count
            summary = self.data_manager.get_data_summary()
            records_per_symbol = summary.get('records_per_symbol', {})
            top_symbols = sorted(records_per_symbol.items(), key=lambda x: x[1], reverse=True)[:5]
            symbols = [symbol for symbol, _ in top_symbols]
        
        quality_report = {}
        
        for symbol in symbols:
            print(f"\n📊 Checking {symbol}...")
            data = self.data_manager.get_data_from_database(symbols=symbol)
            
            if data.empty:
                print(f"  ❌ No data available")
                continue
            
            # Convert timestamp
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data = data.sort_values('timestamp')
            
            # Check for missing values
            missing_values = data.isnull().sum()
            has_missing = missing_values.sum() > 0
            
            # Check for duplicate timestamps
            duplicates = data.duplicated(subset=['timestamp']).sum()
            
            # Check for price anomalies
            price_anomalies = (
                (data['high'] < data['low']) |
                (data['high'] < data['open']) |
                (data['high'] < data['close']) |
                (data['low'] > data['open']) |
                (data['low'] > data['close'])
            ).sum()
            
            # Check for volume anomalies
            volume_anomalies = (data['volume'] <= 0).sum() if 'volume' in data.columns else 0
            
            # Check date gaps
            date_gaps = []
            for i in range(1, len(data)):
                expected_date = data['timestamp'].iloc[i-1] + timedelta(days=1)
                actual_date = data['timestamp'].iloc[i]
                if actual_date.date() != expected_date.date():
                    date_gaps.append((expected_date.date(), actual_date.date()))
            
            quality_report[symbol] = {
                'total_records': len(data),
                'date_range': {
                    'start': data['timestamp'].min().strftime('%Y-%m-%d'),
                    'end': data['timestamp'].max().strftime('%Y-%m-%d')
                },
                'missing_values': missing_values.to_dict() if has_missing else None,
                'duplicate_timestamps': duplicates,
                'price_anomalies': price_anomalies,
                'volume_anomalies': volume_anomalies,
                'date_gaps': len(date_gaps),
                'quality_score': 'Good' if (duplicates == 0 and price_anomalies == 0 and volume_anomalies == 0) else 'Issues Found'
            }
            
            # Print results
            print(f"  📅 Date Range: {quality_report[symbol]['date_range']['start']} to {quality_report[symbol]['date_range']['end']}")
            print(f"  📊 Total Records: {quality_report[symbol]['total_records']:,}")
            print(f"  🔍 Quality Score: {quality_report[symbol]['quality_score']}")
            
            if duplicates > 0:
                print(f"  ⚠️  Duplicate Timestamps: {duplicates}")
            if price_anomalies > 0:
                print(f"  ⚠️  Price Anomalies: {price_anomalies}")
            if volume_anomalies > 0:
                print(f"  ⚠️  Volume Anomalies: {volume_anomalies}")
            if len(date_gaps) > 0:
                print(f"  ⚠️  Date Gaps: {len(date_gaps)}")
        
        return quality_report

def main():
    """Command-line interface for data workflow"""
    parser = argparse.ArgumentParser(description='Complete data workflow pipeline')
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL'], 
                       help='Symbols to process')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--export-formats', nargs='+', default=['csv', 'json'], 
                       choices=['csv', 'json', 'backtest'], help='Export formats')
    parser.add_argument('--no-analysis', action='store_true', 
                       help='Skip data analysis step')
    parser.add_argument('--overview', action='store_true', 
                       help='Show quick data overview only')
    parser.add_argument('--quality-check', action='store_true', 
                       help='Run data quality check only')
    
    args = parser.parse_args()
    
    workflow = DataWorkflow()
    
    if args.overview:
        workflow.quick_data_overview(args.symbols)
    elif args.quality_check:
        workflow.data_quality_check(args.symbols)
    else:
        workflow.run_complete_workflow(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            export_formats=args.export_formats,
            create_analysis=not args.no_analysis
        )

if __name__ == "__main__":
    main()
