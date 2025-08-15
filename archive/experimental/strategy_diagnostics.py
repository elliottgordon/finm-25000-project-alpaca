# Strategy Diagnostics Tool
# Analyzes signal generation and data availability for debugging

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import logging

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from trading_strategy import RSIMeanReversionStrategy

class StrategyDiagnostics:
    """Diagnostic tool for strategy debugging"""
    
    def __init__(self, db_path='../Step 5: Saving Market Data/market_data.db'):
        self.db_path = db_path
        self.strategy = RSIMeanReversionStrategy()
        
        # Top assets from screening
        self.top_assets = ['XLI', 'EFA', 'VWO', 'XLK', 'EEM', 'DIA', 'VEA', 'VTI']
        
    def check_data_availability(self, symbol: str, start_date: str = '2023-01-01', end_date: str = '2024-12-31'):
        """Check data availability for a symbol in date range"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT COUNT(*) as record_count,
                   MIN(date(timestamp)) as first_date,
                   MAX(date(timestamp)) as last_date
            FROM market_data 
            WHERE symbol = ? 
            AND date(timestamp) >= date(?) 
            AND date(timestamp) <= date(?)
        """
        
        result = pd.read_sql_query(query, conn, params=[symbol, start_date, end_date])
        conn.close()
        
        return result.iloc[0].to_dict()
    
    def analyze_signals_for_symbol(self, symbol: str, days: int = 500):
        """Analyze signal generation for a specific symbol"""
        print(f"\n🔍 ANALYZING {symbol}")
        print("-" * 40)
        
        # Get data availability
        data_info = self.check_data_availability(symbol)
        print(f"Records in 2023-2024: {data_info['record_count']}")
        print(f"Date range: {data_info['first_date']} to {data_info['last_date']}")
        
        # Get full data
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT timestamp, close, high, low, open, volume
            FROM market_data 
            WHERE symbol = ? 
            ORDER BY timestamp ASC
        """
        
        df = pd.read_sql_query(query, conn, params=[symbol])
        conn.close()
        
        if df.empty:
            print("❌ No data available")
            return
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        print(f"Total records: {len(df)}")
        print(f"Full date range: {df.index.min().date()} to {df.index.max().date()}")
        
        # Calculate indicators
        if len(df) >= 50:
            try:
                rsi = self.strategy.calculate_rsi(df['close'])
                z_score, rolling_mean, rolling_std = self.strategy.calculate_mean_reversion_signal(df['close'])
                
                # Signal analysis
                buy_signals = (rsi < 30) & (z_score < -2.0)
                sell_signals = (rsi > 70) & (z_score > 2.0)
                
                print(f"\nTechnical Analysis:")
                print(f"   RSI range: {rsi.min():.1f} to {rsi.max():.1f}")
                print(f"   RSI < 30: {(rsi < 30).sum()} times ({(rsi < 30).mean():.1%})")
                print(f"   RSI > 70: {(rsi > 70).sum()} times ({(rsi > 70).mean():.1%})")
                print(f"   Z-score range: {z_score.min():.2f} to {z_score.max():.2f}")
                print(f"   Z-score < -2: {(z_score < -2).sum()} times ({(z_score < -2).mean():.1%})")
                print(f"   Z-score > 2: {(z_score > 2).sum()} times ({(z_score > 2).mean():.1%})")
                
                print(f"\nSignal Generation:")
                print(f"   Buy signals: {buy_signals.sum()}")
                print(f"   Sell signals: {sell_signals.sum()}")
                print(f"   Total signals: {buy_signals.sum() + sell_signals.sum()}")
                
                # Recent signals (last 100 days)
                recent_data = df.tail(100)
                if len(recent_data) > 20:
                    recent_rsi = self.strategy.calculate_rsi(recent_data['close'])
                    recent_z_score, _, _ = self.strategy.calculate_mean_reversion_signal(recent_data['close'])
                    recent_buy = (recent_rsi < 30) & (recent_z_score < -2.0)
                    recent_sell = (recent_rsi > 70) & (recent_z_score > 2.0)
                    
                    print(f"\nRecent Activity (last 100 records):")
                    print(f"   Buy signals: {recent_buy.sum()}")
                    print(f"   Sell signals: {recent_sell.sum()}")
                    
                    if recent_buy.any():
                        last_buy = recent_data[recent_buy].index[-1]
                        print(f"   Last buy signal: {last_buy.date()}")
                    
                    if recent_sell.any():
                        last_sell = recent_data[recent_sell].index[-1]
                        print(f"   Last sell signal: {last_sell.date()}")
                
                # Show some recent values
                print(f"\nCurrent Values:")
                print(f"   Price: ${df['close'].iloc[-1]:.2f}")
                print(f"   RSI: {rsi.iloc[-1]:.1f}")
                print(f"   Z-score: {z_score.iloc[-1]:.2f}")
                
            except Exception as e:
                print(f"❌ Error calculating indicators: {str(e)}")
        
        else:
            print("❌ Insufficient data for analysis")
    
    def run_full_diagnostics(self):
        """Run diagnostics on all top assets"""
        print("=" * 80)
        print("STRATEGY DIAGNOSTICS REPORT")
        print("=" * 80)
        
        print(f"\n📋 ANALYZING TOP {len(self.top_assets)} ASSETS FOR RSI + MEAN REVERSION")
        
        for symbol in self.top_assets:
            try:
                self.analyze_signals_for_symbol(symbol)
            except Exception as e:
                print(f"\n❌ ERROR ANALYZING {symbol}: {str(e)}")
        
        # Summary analysis
        print(f"\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        total_signals = 0
        working_assets = 0
        
        for symbol in self.top_assets:
            try:
                conn = sqlite3.connect(self.db_path)
                query = "SELECT timestamp, close FROM market_data WHERE symbol = ? ORDER BY timestamp ASC"
                df = pd.read_sql_query(query, conn, params=[symbol])
                conn.close()
                
                if not df.empty and len(df) >= 50:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    
                    rsi = self.strategy.calculate_rsi(df['close'])
                    z_score, _, _ = self.strategy.calculate_mean_reversion_signal(df['close'])
                    
                    buy_signals = (rsi < 30) & (z_score < -2.0)
                    sell_signals = (rsi > 70) & (z_score > 2.0)
                    
                    asset_signals = buy_signals.sum() + sell_signals.sum()
                    total_signals += asset_signals
                    working_assets += 1
                    
            except:
                continue
        
        print(f"Working assets: {working_assets}/{len(self.top_assets)}")
        print(f"Total signals across all assets: {total_signals}")
        print(f"Average signals per asset: {total_signals/working_assets if working_assets > 0 else 0:.1f}")

def main():
    """Run diagnostics"""
    diagnostics = StrategyDiagnostics()
    diagnostics.run_full_diagnostics()

if __name__ == "__main__":
    main()
