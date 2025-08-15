#!/usr/bin/env python3
"""
Quick Data Check for Step 4
Check current data status and identify gaps
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

def check_data_status():
    """Check current data status"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
    watchlist_path = os.path.join(os.path.dirname(__file__), 'watchlist.txt')
    
    print("🔍 QUICK DATA STATUS CHECK")
    print("=" * 50)
    
    # Load watchlist
    try:
        with open(watchlist_path, 'r') as f:
            lines = f.readlines()
        
        watchlist_symbols = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('='):
                watchlist_symbols.append(line)
        
        print(f"📋 Watchlist: {len(watchlist_symbols)} symbols")
        
    except Exception as e:
        print(f"❌ Error loading watchlist: {e}")
        return
    
    # Check database
    try:
        conn = sqlite3.connect(db_path)
        
        # Overall stats
        total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM market_data").fetchone()[0]
        total_records = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
        
        print(f"💾 Database: {total_symbols} symbols, {total_records:,} records")
        
        # Check each watchlist symbol
        print(f"\n📊 SYMBOL STATUS:")
        print("-" * 50)
        
        missing_symbols = []
        outdated_symbols = []
        current_symbols = []
        
        eastern = pytz.timezone('US/Eastern')
        today = eastern.localize(datetime.now())
        cutoff_date = (today - timedelta(days=2)).isoformat()
        
        for symbol in watchlist_symbols:
            query = """
                SELECT COUNT(*) as count, MAX(timestamp) as latest
                FROM market_data 
                WHERE symbol = ?
            """
            
            result = conn.execute(query, (symbol,)).fetchone()
            
            if result[0] == 0:
                missing_symbols.append(symbol)
                print(f"❌ {symbol:<6} - MISSING")
            else:
                latest = result[1]
                if latest and latest >= cutoff_date:
                    current_symbols.append(symbol)
                    print(f"✅ {symbol:<6} - CURRENT ({result[0]:>4} records)")
                else:
                    outdated_symbols.append(symbol)
                    print(f"⚠️  {symbol:<6} - OUTDATED ({result[0]:>4} records, last: {latest[:10] if latest else 'N/A'})")
        
        conn.close()
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print("-" * 50)
        print(f"   Total Watchlist Symbols: {len(watchlist_symbols)}")
        print(f"   Current Data: {len(current_symbols)}")
        print(f"   Outdated Data: {len(outdated_symbols)}")
        print(f"   Missing Data: {len(missing_symbols)}")
        
        if missing_symbols:
            print(f"\n❌ MISSING SYMBOLS ({len(missing_symbols)}):")
            print("   " + ", ".join(missing_symbols))
        
        if outdated_symbols:
            print(f"\n⚠️  OUTDATED SYMBOLS ({len(outdated_symbols)}):")
            print("   " + ", ".join(outdated_symbols[:20]))  # Show first 20
            if len(outdated_symbols) > 20:
                print(f"   ... and {len(outdated_symbols) - 20} more")
        
        # Recommendations
        print(f"\n🎯 RECOMMENDATIONS:")
        if missing_symbols or outdated_symbols:
            print(f"   • Run comprehensive data collection to fill gaps")
            print(f"   • Set up daily incremental updates")
            print(f"   • Schedule weekly full updates")
        else:
            print(f"   • All data is current!")
            print(f"   • Set up daily incremental updates to maintain freshness")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def check_specific_symbols():
    """Check specific symbols in detail"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
    
    print(f"\n🔍 DETAILED SYMBOL CHECK")
    print("=" * 50)
    
    # Check major ETFs
    major_etfs = ['SPY', 'QQQ', 'IWM', 'VTI', 'VEA', 'VWO']
    
    try:
        conn = sqlite3.connect(db_path)
        
        for symbol in major_etfs:
            query = """
                SELECT 
                    COUNT(*) as count,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest,
                    AVG(volume) as avg_volume
                FROM market_data 
                WHERE symbol = ?
            """
            
            result = conn.execute(query, (symbol,)).fetchone()
            
            if result[0] > 0:
                print(f"📊 {symbol}:")
                print(f"   Records: {result[0]:,}")
                print(f"   Date Range: {result[1][:10]} to {result[2][:10]}")
                print(f"   Avg Volume: {result[3]:,.0f}")
                
                # Check recent data
                recent_query = """
                    SELECT COUNT(*) FROM market_data 
                    WHERE symbol = ? AND timestamp >= date('now', '-2 days')
                """
                recent_count = conn.execute(recent_query, (symbol,)).fetchone()[0]
                print(f"   Recent (2 days): {recent_count} records")
                print()
            else:
                print(f"❌ {symbol}: NO DATA")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking symbols: {e}")

def main():
    """Main function"""
    print("🚀 QUICK DATA CHECK")
    print("=" * 50)
    
    check_data_status()
    check_specific_symbols()
    
    print("\n💡 NEXT STEPS:")
    print("   1. Run 'python comprehensive_data_collector.py' to collect missing data")
    print("   2. Run 'python data_update_scheduler.py' to set up automatic updates")
    print("   3. Use 'python quick_data_check.py' to monitor progress")

if __name__ == "__main__":
    main()
