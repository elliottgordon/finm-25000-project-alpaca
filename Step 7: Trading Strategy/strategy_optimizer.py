# Step 7: Trading Strategy Optimization
# A script to systematically test different strategy parameters to find the optimal combination for a portfolio.

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from trading_strategy import BollingerBandMeanReversionStrategy
import logging
from typing import List

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_assets_from_db() -> List[str]:
    """Gets all unique assets available in the market_data database."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
        conn = sqlite3.connect(db_path)
        query = "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
        db_symbols = pd.read_sql_query(query, conn)['symbol'].tolist()
        conn.close()
        logging.info(f"Found {len(db_symbols)} unique assets in the database for optimization.")
        return db_symbols
    except Exception as e:
        logging.error(f"Could not get assets from database: {e}")
        return []

def run_portfolio_optimization():
    """
    Performs a grid search to find the best Bollinger Band parameters for a portfolio of symbols.
    """
    # 1. Get all symbols to test
    symbols_to_test = get_all_assets_from_db()
    if not symbols_to_test:
        print("No symbols found in the database. Exiting optimization.")
        return

    # 2. Define the parameter ranges to test
    windows = np.arange(10, 60, 10)  # Test windows from 10 to 50, in steps of 10
    std_devs = np.arange(1.5, 3.25, 0.5) # Test std deviations from 1.5 to 3.0, in steps of 0.5

    results = []
    
    print("\n" + "="*80)
    print(f"🔬 Starting Parameter Optimization for {len(symbols_to_test)} symbols")
    print("="*80)
    
    total_runs = len(symbols_to_test) * len(windows) * len(std_devs)
    current_run = 0

    # 3. Loop through every symbol and every combination of parameters
    for symbol in symbols_to_test:
        for window in windows:
            for std_dev in std_devs:
                current_run += 1
                print(f"Running backtest {current_run}/{total_runs}: Symbol={symbol}, Window={window}, Std Dev={std_dev:.2f}")

                strategy = BollingerBandMeanReversionStrategy(window=window, std_dev=std_dev)
                backtest_result = strategy.backtest_strategy(symbol=symbol)

                if backtest_result and 'sharpe_ratio' in backtest_result:
                    results.append({
                        'symbol': symbol,
                        'window': window,
                        'std_dev': std_dev,
                        'sharpe_ratio': backtest_result['sharpe_ratio'],
                        'total_return': backtest_result['total_return'],
                        'win_rate': backtest_result['win_rate'],
                        'total_trades': backtest_result['total_trades']
                    })

    print("\n" + "="*80)
    print("✅ Optimization Complete!")
    print("="*80)

    if not results:
        print("No valid backtests were completed. Please check your data and strategy logic.")
        return

    # 4. Find the best parameters based on average performance across all symbols
    results_df = pd.DataFrame(results)
    
    # Group by parameters and calculate the mean Sharpe ratio for each combination
    performance_summary = results_df.groupby(['window', 'std_dev'])['sharpe_ratio'].mean()
    
    # Find the parameter set with the highest average Sharpe ratio
    best_params = performance_summary.idxmax()
    best_window, best_std_dev = best_params

    print("\n🏆 Best Overall Parameters (Optimized for Average Sharpe Ratio across all assets):")
    print(f"   - Bollinger Window: {int(best_window)}")
    print(f"   - Standard Deviations: {best_std_dev:.2f}")
    
    # Show the average performance for the best parameter set
    best_results_df = results_df[(results_df['window'] == best_window) & (results_df['std_dev'] == best_std_dev)]
    
    print("\n📈 Average Performance with Best Parameters:")
    print(f"   - Average Sharpe Ratio: {best_results_df['sharpe_ratio'].mean():.2f}")
    print(f"   - Average Total Return: {best_results_df['total_return'].mean():.2%}")
    print(f"   - Average Win Rate: {best_results_df['win_rate'].mean():.2%}")
    print(f"   - Average Total Trades: {best_results_df['total_trades'].mean():.1f}")

if __name__ == "__main__":
    run_portfolio_optimization()
