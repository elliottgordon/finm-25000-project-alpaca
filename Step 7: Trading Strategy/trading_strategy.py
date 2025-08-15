# Step 7: Develop a Trading Strategy - Professional Implementation
# Comprehensive Mean Reversion Strategy using Bollinger Bands

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import pytz
import logging
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import Alpaca API
try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logging.warning("Alpaca API not available - running in simulation mode")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_strategy.log'),
        logging.StreamHandler()
    ]
)

class BollingerBandMeanReversionStrategy:
    """
    Implements a mean reversion strategy using Bollinger Bands for signal generation.
    """
    
    def __init__(self, db_path=None, window: int = 20, std_dev: float = 2.5):
        # Database setup
        if db_path is None:
            self.db_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '../Step 5: Saving Market Data/market_data.db'))
        else:
            self.db_path = db_path

        # 1. DEFINE TRADING GOALS
        self.trading_goals = {
            'primary_objective': 'Implement a robust Bollinger Band mean reversion strategy',
            'return_target': 'Consistent alpha from short-term price reversions',
            'risk_tolerance': 'Moderate',
            'time_horizon': 'Short-term (1-10 days per trade)',
        }

        # 2. TECHNICAL INDICATORS AND SIGNALS (Now accepts dynamic parameters)
        self.strategy_parameters = {
            'bollinger_window': window,
            'bollinger_std_dev': std_dev,
        }

        # Risk Management
        self.risk_parameters = {
            'max_position_size': 0.50,  # 25% max per position
        }

        # API setup (if available)
        if ALPACA_AVAILABLE:
            try:
                from Alpaca_API import ALPACA_KEY, ALPACA_SECRET
                self.trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
                self.data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
                self.api_available = True
            except ImportError:
                self.api_available = False
                logging.warning("Alpaca credentials not found - running in simulation mode")
        else:
            self.api_available = False

        # Suppress INFO logs during optimization runs for cleaner output
        if __name__ != "__main__":
            logging.getLogger().setLevel(logging.WARNING)

    
    def get_historical_data_from_db(self, symbol: str) -> pd.DataFrame:
        """Get ALL historical data from our existing database for a symbol."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT timestamp, close, high, low, open, volume
                FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn, params=[symbol])
            conn.close()
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logging.error(f"Error retrieving historical data: {e}")
            return pd.DataFrame()

    def calculate_bollinger_bands(self, prices: pd.Series) -> pd.DataFrame:
        """Calculates Bollinger Bands."""
        window = self.strategy_parameters['bollinger_window']
        std_dev = self.strategy_parameters['bollinger_std_dev']
        
        rolling_mean = prices.rolling(window=window).mean()
        rolling_std = prices.rolling(window=window).std()
        
        upper_band = rolling_mean + (rolling_std * std_dev)
        lower_band = rolling_mean - (rolling_std * std_dev)
        
        return pd.DataFrame({
            'middle_band': rolling_mean,
            'upper_band': upper_band,
            'lower_band': lower_band
        })

    def generate_trading_signals(self, symbol: str = 'SPY') -> pd.DataFrame:
        """
        Generate trading signals based on Bollinger Band crossovers.
        """
        data = self.get_historical_data_from_db(symbol)
        
        if data.empty:
            return pd.DataFrame()
        
        bbands = self.calculate_bollinger_bands(data['close'])
        data = data.join(bbands)
        
        data['signal'] = 0
        data['prev_close'] = data['close'].shift(1)

        buy_condition = (data['close'] < data['lower_band']) & (data['prev_close'] >= data['lower_band'].shift(1))
        data.loc[buy_condition, 'signal'] = 1
        
        sell_condition = (data['close'] > data['upper_band']) & (data['prev_close'] <= data['upper_band'].shift(1))
        data.loc[sell_condition, 'signal'] = -1

        exit_long_condition = (data['close'] > data['middle_band']) & (data['prev_close'] <= data['middle_band'].shift(1))
        exit_short_condition = (data['close'] < data['middle_band']) & (data['prev_close'] >= data['middle_band'].shift(1))
        data.loc[exit_long_condition | exit_short_condition, 'signal'] = 2
        
        return data
    
    def backtest_strategy(self, symbol: str = 'SPY', initial_capital: float = 100000) -> Dict:
        data = self.generate_trading_signals(symbol)
        
        if data.empty:
            return {}
        
        capital = initial_capital
        position = 0
        position_size = 0
        entry_price = 0
        trades = []
        equity_curve = []
        daily_returns = []
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = row['close']
            signal = row['signal']
            
            current_equity = capital + (position_size * (current_price - entry_price) if position != 0 else 0)
            equity_curve.append({'timestamp': timestamp, 'equity': current_equity})

            if i > 0:
                prev_equity = equity_curve[i-1]['equity']
                daily_return = (current_equity - prev_equity) / prev_equity if prev_equity != 0 else 0
                daily_returns.append(daily_return)

            if signal == 2 and position != 0:
                pnl = (current_price - entry_price) * position_size * position
                capital += pnl
                trades.append({'exit_date': timestamp, 'pnl': pnl})
                position = 0
                position_size = 0

            elif signal == 1 and position == 0:
                position_size = (capital * self.risk_parameters['max_position_size']) / current_price
                entry_price = current_price
                position = 1
                trades.append({'entry_date': timestamp, 'price': current_price, 'side': 'buy'})
            
            elif signal == -1 and position == 0:
                position_size = (capital * self.risk_parameters['max_position_size']) / current_price
                entry_price = current_price
                position = -1
                trades.append({'entry_date': timestamp, 'price': current_price, 'side': 'sell'})

        if not trades:
            return {'message': 'No trades generated'}

        completed_trades = [t for t in trades if 'exit_date' in t]
        total_trades = len(completed_trades)
        profitable_trades = len([t for t in completed_trades if 'pnl' in t and t['pnl'] > 0])
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        total_return = (equity_curve[-1]['equity'] - initial_capital) / initial_capital

        equity_df = pd.DataFrame(equity_curve).set_index('timestamp')
        running_max = equity_df['equity'].cummax()
        drawdown = (equity_df['equity'] - running_max) / running_max
        max_drawdown = drawdown.min()

        sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0

        return {
            'symbol': symbol,
            'total_return': total_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'equity_curve': equity_curve,
            'daily_returns': daily_returns
        }
    
    def run_comprehensive_backtest(self, symbols: List[str] = None, initial_capital: float = 100000) -> Dict:
        if symbols is None:
            symbols = self._get_available_symbols_from_db()
        
        individual_results = {}
        for symbol in symbols:
            symbol_capital = initial_capital / len(symbols) if len(symbols) > 0 else initial_capital
            result = self.backtest_strategy(symbol, symbol_capital)
            if result and 'total_return' in result:
                individual_results[symbol] = result
        
        successful_results = [r for r in individual_results.values() if r and 'total_return' in r]
        
        if successful_results:
            portfolio_metrics = {
                'avg_return': np.mean([r['total_return'] for r in successful_results]),
                'avg_win_rate': np.mean([r['win_rate'] for r in successful_results]),
                'avg_sharpe': np.mean([r['sharpe_ratio'] for r in successful_results]),
                'avg_drawdown': np.mean([r['max_drawdown'] for r in successful_results]),
            }
        else:
            portfolio_metrics = {}

        return {
            'individual_results': individual_results,
            'portfolio_metrics': portfolio_metrics
        }

if __name__ == "__main__":
    strategy = BollingerBandMeanReversionStrategy()
    results = strategy.run_comprehensive_backtest()
    
    print("\n" + "="*80)
    print("COMPREHENSIVE BACKTEST COMPLETE")
    print("="*80)
    
    if results['portfolio_metrics']:
        metrics = results['portfolio_metrics']
        print(f"Portfolio Average Return: {metrics.get('avg_return', 0):.2%}")
        print(f"Portfolio Average Win Rate: {metrics.get('avg_win_rate', 0):.2%}")
        print(f"Portfolio Average Sharpe Ratio: {metrics.get('avg_sharpe', 0):.2f}")
        print(f"Portfolio Average Max Drawdown: {metrics.get('avg_drawdown', 0):.2%}")
