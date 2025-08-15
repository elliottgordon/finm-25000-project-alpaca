# Step 7: Trading Strategy Analysis and Visualization
# Comprehensive analysis of RSI + Mean Reversion Strategy with Professional Backtesting

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import json

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import our strategy from the existing trading_strategy.py file
try:
    from trading_strategy import BollingerBandMeanReversionStrategy
except ImportError:
    print("Error: Could not import BollingerBandMeanReversionStrategy. Make sure trading_strategy.py is in the parent directory.")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StrategyAnalyzer:
    """
    Analyzes and visualizes the performance of a trading strategy.
    Can run analysis on a single asset or a full portfolio.
    """
    
    def __init__(self, output_dir: str = 'analysis_outputs'):
        """Initializes the StrategyAnalyzer."""
        self.strategy = BollingerBandMeanReversionStrategy()
        self.analysis_dir = output_dir
        self._setup_environment()
        logging.info("StrategyAnalyzer initialized.")

    def _setup_environment(self):
        """Sets up the analysis directory and plotting styles."""
        if not os.path.exists(self.analysis_dir):
            os.makedirs(self.analysis_dir)
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("viridis")

    def _get_db_connection(self) -> Optional[sqlite3.Connection]:
        """Establishes and returns a connection to the market data database."""
        try:
            db_path = os.path.join(PARENT_DIR, 'Step 5: Saving Market Data', 'market_data.db')
            return sqlite3.connect(db_path)
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")
            return None

    def get_all_assets_from_db(self) -> List[str]:
        """Gets all unique assets available in the market_data database."""
        conn = self._get_db_connection()
        if not conn:
            return []
        try:
            query = "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
            db_symbols = pd.read_sql_query(query, conn)['symbol'].tolist()
            logging.info(f"Found {len(db_symbols)} unique assets in the database.")
            return db_symbols
        finally:
            conn.close()

    def _calculate_performance_metrics(self, daily_returns: pd.Series) -> Dict:
        """Calculates key performance metrics from a series of daily returns."""
        if daily_returns.empty or daily_returns.std() == 0:
            return {'return': 0, 'volatility': 0, 'sharpe': 0}
            
        cumulative_return = (1 + daily_returns).prod()
        trading_days = len(daily_returns)
        years = trading_days / 252.0
        annualized_return = (cumulative_return ** (1/years)) - 1 if years > 0 else 0
        annualized_volatility = daily_returns.std() * np.sqrt(252)
        sharpe_ratio = (daily_returns.mean() * 252) / annualized_volatility if annualized_volatility > 0 else 0
        
        return {
            'return': annualized_return,
            'volatility': annualized_volatility,
            'sharpe': sharpe_ratio
        }

    def run_single_asset_analysis(self, symbol: str):
        """Runs a backtest for a single asset and visualizes the results."""
        print("\n" + "="*80)
        print(f"🔬 Analyzing Strategy Performance for: {symbol}")
        print("="*80)
        
        results = self.strategy.backtest_strategy(symbol)
        
        if not results or 'total_return' not in results:
            logging.error(f"Backtest for {symbol} failed or generated no trades.")
            return

        equity_curve_df = pd.DataFrame(results['equity_curve']).set_index('timestamp')
        equity_curve = (equity_curve_df['equity'] / equity_curve_df['equity'].iloc[0]) * 100
        
        daily_returns = pd.Series(results['daily_returns'], index=equity_curve_df.index[1:])
        strategy_metrics = self._calculate_performance_metrics(daily_returns)

        spy_data = self.strategy.get_historical_data_from_db('SPY')
        benchmark_equity = None
        benchmark_metrics = None
        if not spy_data.empty:
            spy_data.index = pd.to_datetime(spy_data.index)
            equity_curve.index = pd.to_datetime(equity_curve.index)
            
            common_dates = equity_curve.index.intersection(spy_data.index)
            equity_curve = equity_curve.loc[common_dates]
            spy_data = spy_data.loc[common_dates]

            benchmark_equity = (spy_data['close'] / spy_data['close'].iloc[0]) * 100
            benchmark_daily_returns = spy_data['close'].pct_change().fillna(0)
            benchmark_metrics = self._calculate_performance_metrics(benchmark_daily_returns)
            
        self.create_single_asset_visualization(symbol, equity_curve, benchmark_equity, strategy_metrics, benchmark_metrics)

    def create_single_asset_visualization(self, symbol: str, equity_curve: pd.Series, benchmark_equity: Optional[pd.Series], strategy_metrics: Dict, benchmark_metrics: Optional[Dict]):
        """Generates and saves a visualization for a single asset backtest."""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        ax.plot(equity_curve.index, equity_curve, label=f'{symbol} Strategy Equity', color='navy', linewidth=2)
        if benchmark_equity is not None:
            ax.plot(benchmark_equity.index, benchmark_equity, label='SPY Benchmark', color='grey', linestyle='--', linewidth=2)
        
        ax.set_title(f'{symbol} Performance vs. SPY Benchmark', fontsize=18, fontweight='bold')
        ax.set_ylabel('Normalized Growth (Initial = 100)')
        ax.legend(loc='upper left')
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)

        stats_text = "--- Performance ---\n\n"
        stats_text += f"{symbol} Strategy:\n"
        stats_text += f"  Annualized Return: {strategy_metrics['return']:.2%}\n"
        stats_text += f"  Annualized Volatility: {strategy_metrics['volatility']:.2%}\n"
        stats_text += f"  Sharpe Ratio: {strategy_metrics['sharpe']:.2f}\n"
        if benchmark_metrics:
            stats_text += "\nSPY Benchmark:\n"
            stats_text += f"  Annualized Return: {benchmark_metrics['return']:.2%}\n"
            stats_text += f"  Annualized Volatility: {benchmark_metrics['volatility']:.2%}\n"
            stats_text += f"  Sharpe Ratio: {benchmark_metrics['sharpe']:.2f}"

        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))

        plt.tight_layout()
        self._save_plot(f'analysis_{symbol}')
        plt.show()

    def run_portfolio_analysis(self):
        """Runs a backtest across all available assets and visualizes the results."""
        print("\n" + "="*80)
        print("🔬 Analyzing Strategy Performance for Full Portfolio")
        print("="*80)
        
        symbols_to_test = self.get_all_assets_from_db()
        if not symbols_to_test:
            logging.error("No symbols found for portfolio analysis.")
            return

        portfolio_results = self.strategy.run_comprehensive_backtest(symbols_to_test)
        if 'portfolio_metrics' not in portfolio_results:
            logging.error("Portfolio backtest failed.")
            return

        all_returns = [pd.Series(res['daily_returns'], index=pd.to_datetime(pd.DataFrame(res['equity_curve']).set_index('timestamp').index[1:])) for res in portfolio_results['individual_results'].values() if res and 'daily_returns' in res]
        if not all_returns:
            logging.error("No daily returns to analyze.")
            return

        portfolio_daily_returns = pd.concat(all_returns, axis=1).fillna(0).mean(axis=1)
        portfolio_equity = (1 + portfolio_daily_returns).cumprod() * 100
        portfolio_equity.iloc[0] = 100
        strategy_metrics = self._calculate_performance_metrics(portfolio_daily_returns)

        spy_data = self.strategy.get_historical_data_from_db('SPY')
        benchmark_equity, benchmark_metrics = None, None
        if not spy_data.empty:
            spy_data.index = pd.to_datetime(spy_data.index)
            common_dates = portfolio_equity.index.intersection(spy_data.index)
            portfolio_equity, spy_data = portfolio_equity.loc[common_dates], spy_data.loc[common_dates]
            benchmark_equity = (spy_data['close'] / spy_data['close'].iloc[0]) * 100
            benchmark_daily_returns = spy_data['close'].pct_change().fillna(0)
            benchmark_metrics = self._calculate_performance_metrics(benchmark_daily_returns)
            
        self.create_portfolio_visualization(portfolio_results, portfolio_equity, benchmark_equity, strategy_metrics, benchmark_metrics)

    def create_portfolio_visualization(self, results: Dict, portfolio_equity: pd.Series, benchmark_equity: Optional[pd.Series], strategy_metrics: Dict, benchmark_metrics: Optional[Dict]):
        """Generates and saves a visualization summarizing portfolio performance."""
        df = pd.DataFrame([{'symbol': s, 'return': r['total_return'], 'win_rate': r['win_rate'], 'sharpe': r.get('sharpe_ratio', 0)} for s, r in results['individual_results'].items() if r and 'total_return' in r]).sort_values('return', ascending=False)
        if df.empty:
            logging.warning("No valid backtest results to plot.")
            return

        fig = plt.figure(figsize=(20, 15))
        gs = fig.add_gridspec(2, 2)
        fig.suptitle('Portfolio Performance Summary', fontsize=22, fontweight='bold')

        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(portfolio_equity.index, portfolio_equity, label='Strategy Equity Curve', color='navy', linewidth=2)
        if benchmark_equity is not None:
            ax1.plot(benchmark_equity.index, benchmark_equity, label='SPY Benchmark', color='grey', linestyle='--', linewidth=2)
        ax1.set_title('Portfolio Growth vs. SPY Benchmark', fontsize=16)
        ax1.set_ylabel('Normalized Growth (Initial = 100)')
        ax1.legend(loc='upper left')
        ax1.grid(True, which='both', linestyle='--', linewidth=0.5)

        stats_text = f"--- Performance ---\n\nStrategy:\n  Annualized Return: {strategy_metrics['return']:.2%}\n  Annualized Volatility: {strategy_metrics['volatility']:.2%}\n  Sharpe Ratio: {strategy_metrics['sharpe']:.2f}\n"
        if benchmark_metrics:
            stats_text += f"\nSPY Benchmark:\n  Annualized Return: {benchmark_metrics['return']:.2%}\n  Annualized Volatility: {benchmark_metrics['volatility']:.2%}\n  Sharpe Ratio: {benchmark_metrics['sharpe']:.2f}"
        ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes, fontsize=12, verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))

        ax2 = fig.add_subplot(gs[1, 0])
        display_df = pd.concat([df.head(15), df.tail(15)]) if len(df) > 30 else df
        ax2.set_title(f'Total Return by Symbol (Top & Bottom {min(15, len(df))})', fontsize=14)
        sns.barplot(x='symbol', y='return', data=display_df, ax=ax2, palette='viridis')
        ax2.set_ylabel('Total Return')
        ax2.tick_params(axis='x', rotation=45, labelsize=10)
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0%}'))

        ax3 = fig.add_subplot(gs[1, 1])
        sns.scatterplot(x='win_rate', y='sharpe', size='return', data=df, ax=ax3, sizes=(50, 500), legend=False, alpha=0.7)
        ax3.set_title('Win Rate vs. Sharpe Ratio', fontsize=14)
        ax3.set_xlabel('Win Rate')
        ax3.set_ylabel('Sharpe Ratio')
        ax3.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0%}'))
        for _, row in df.head(10).iterrows():
            ax3.text(row['win_rate'] * 1.01, row['sharpe'], row['symbol'], fontsize=9)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        self._save_plot('analysis_portfolio')
        plt.show()

    def _save_plot(self, name: str):
        """Saves the current plot to a file in the analysis directory."""
        filename = os.path.join(self.analysis_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.png")
        try:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logging.info(f"Plot saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save plot: {e}")

def main():
    """Main function to run the strategy analysis."""
    analyzer = StrategyAnalyzer()
    
    print("\n" + "="*80)
    print("🔬 Strategy Analyzer")
    print("="*80)
    print("Choose an analysis to run:")
    print("  1. Analyze a single asset")
    print("  2. Analyze the full portfolio")

    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == '1':
        symbol = input("Enter the stock symbol to analyze (e.g., AAPL): ").strip().upper()
        if symbol:
            analyzer.run_single_asset_analysis(symbol)
        else:
            print("Invalid symbol. Exiting.")
    elif choice == '2':
        analyzer.run_portfolio_analysis()
    else:
        print("Invalid choice. Please run the script again and enter 1 or 2.")

    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print(f"📊 Check the '{analyzer.analysis_dir}' directory for the chart.")
    print("="*80)

if __name__ == "__main__":
    main()
