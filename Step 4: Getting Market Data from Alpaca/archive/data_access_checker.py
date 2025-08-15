#!/usr/bin/env python3
"""
Data Access Checker for Alpaca API
Checks what data access levels are available with current subscription
"""

import os
import sys
from datetime import datetime, timedelta
import pytz

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_api import make_client, get_daily_bars
from step4_config import get_credentials

def check_data_access():
    """Check what data access levels are available"""
    print("🔍 ALPACA DATA ACCESS CHECKER")
    print("=" * 50)
    
    try:
        # Test basic client connection
        print("📡 Testing Alpaca API connection...")
        client = make_client()
        print("✅ API connection successful")
        
        # Test daily data access
        print("\n📊 Testing daily data access...")
        eastern = pytz.timezone('US/Eastern')
        end_date = eastern.localize(datetime.now())
        start_date = end_date - timedelta(days=5)
        
        try:
            daily_data = get_daily_bars(['SPY'], start_date, end_date)
            if not daily_data.empty:
                print(f"✅ Daily data access: SUCCESS")
                print(f"   Retrieved {len(daily_data)} daily bars for SPY")
                print(f"   Date range: {daily_data['timestamp'].min()} to {daily_data['timestamp'].max()}")
            else:
                print("⚠️  Daily data access: No data returned")
        except Exception as e:
            print(f"❌ Daily data access: FAILED - {e}")
        
        # Test minute data access (this will likely fail with free account)
        print("\n⏰ Testing minute data access...")
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            req = StockBarsRequest(
                symbol_or_symbols=['SPY'],
                timeframe=TimeFrame.Minute,
                start=start_date,
                end=end_date,
            )
            
            resp = client.get_stock_bars(req)
            if resp and hasattr(resp, 'data') and resp.data:
                print("✅ Minute data access: SUCCESS")
                print(f"   Retrieved minute bars for SPY")
            else:
                print("⚠️  Minute data access: Limited or no data")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "subscription" in error_msg and "sip" in error_msg:
                print("❌ Minute data access: REQUIRES PAID SUBSCRIPTION")
                print("   Your free account doesn't have access to real-time SIP data")
                print("   You need Market Data Pro or higher for minute-level data")
            elif "rate limit" in error_msg:
                print("⚠️  Minute data access: RATE LIMITED")
            else:
                print(f"❌ Minute data access: FAILED - {e}")
        
        # Test real-time quote access
        print("\n💬 Testing real-time quote access...")
        try:
            from step4_api import get_latest_quotes
            quotes = get_latest_quotes(['SPY'])
            if quotes:
                print("✅ Real-time quotes: SUCCESS")
            else:
                print("⚠️  Real-time quotes: Limited access")
        except Exception as e:
            print(f"❌ Real-time quotes: FAILED - {e}")
        
        # Summary and recommendations
        print("\n📋 DATA ACCESS SUMMARY:")
        print("=" * 50)
        print("✅ DAILY DATA: Available (OHLCV bars)")
        print("❌ MINUTE DATA: Requires paid subscription")
        print("⚠️  REAL-TIME: Limited with free account")
        
        print("\n💡 RECOMMENDATIONS:")
        print("1. Use daily data for strategy development")
        print("2. Upgrade to Market Data Pro for intraday trading")
        print("3. Consider alternative data sources for testing")
        print("4. Use daily data with enhanced indicators for now")
        
        print("\n🚀 NEXT STEPS:")
        print("1. Test strategy with daily data first")
        print("2. Optimize parameters for daily timeframe")
        print("3. Upgrade subscription when ready for intraday")
        print("4. Use daily data to validate strategy logic")
        
    except Exception as e:
        print(f"❌ Error checking data access: {e}")

def test_daily_strategy_approach():
    """Test if we can create a daily-based strategy that simulates intraday signals"""
    print("\n🧪 TESTING DAILY STRATEGY APPROACH:")
    print("=" * 50)
    
    try:
        eastern = pytz.timezone('US/Eastern')
        end_date = eastern.localize(datetime.now())
        start_date = end_date - timedelta(days=60)  # 2 months of data
        
        print("📊 Collecting daily data for strategy testing...")
        symbols = ['SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT']
        
        for symbol in symbols:
            try:
                data = get_daily_bars([symbol], start_date, end_date)
                if not data.empty:
                    print(f"✅ {symbol}: {len(data)} daily bars")
                else:
                    print(f"⚠️  {symbol}: No data")
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")
        
        print("\n💡 DAILY STRATEGY APPROACH:")
        print("- Use daily OHLCV data as base")
        print("- Calculate 3-5 day RSI (faster than traditional 14-day)")
        print("- Use daily mean reversion signals")
        print("- Simulate intraday-like signals with daily data")
        print("- Focus on high-frequency daily trading")
        
    except Exception as e:
        print(f"❌ Error testing daily approach: {e}")

if __name__ == "__main__":
    check_data_access()
    test_daily_strategy_approach()
