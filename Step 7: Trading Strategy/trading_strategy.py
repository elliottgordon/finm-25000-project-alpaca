# Step 7: Develop a Trading Strategy
# Implementation following assignment requirements step-by-step

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import pytz
import logging

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from Alpaca_API import ALPACA_KEY, ALPACA_SECRET

# Import Alpaca API
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_strategy.log'),
        logging.StreamHandler()
    ]
)

class RSIMeanReversionStrategy:
    """
    Step 7: Trading Strategy Implementation
    
    Following assignment requirements:
    1. Define Trading Goals
    2. Select Trading Instruments
    3. Technical Indicators and Signals (RSI + Mean Reversion)
    4. Backtesting capability
    5. Paper Trading integration
    6. Real-time Monitoring
    """
    
    def __init__(self, db_path='../Step 5: Saving Market Data/market_data.db'):
        # 1. DEFINE TRADING GOALS (Assignment Step 7.1)
        self.trading_goals = {
            'objective': 'Short-term mean reversion with RSI confirmation',
            'risk_tolerance': 'Moderate',
            'target_return': 'Consistent small gains with limited downside',
            'time_horizon': 'Short-term (1-5 days per trade)'
        }
        
        # 2. SELECT TRADING INSTRUMENTS (Assignment Step 7.2)
        self.trading_instruments = ['SPY', 'VXX']  # Using our existing data
        self.primary_symbol = 'SPY'  # Focus on SPY for main strategy
        
        # 3. TECHNICAL INDICATORS AND SIGNALS (Assignment Step 7.3)
        # RSI Parameters
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
        # Mean Reversion Parameters
        self.lookback_period = 20  # For mean calculation
        self.mean_reversion_threshold = 2.0  # Standard deviations
        
        # Risk Management
        self.position_size = 100  # Share quantity per trade
        self.stop_loss_pct = 0.02  # 2% stop loss
        self.take_profit_pct = 0.01  # 1% take profit
        
        # Database and API setup
        self.db_path = db_path
        self.trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
        self.data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
        
        logging.info("RSI Mean Reversion Strategy initialized")
        logging.info(f"Trading Goals: {self.trading_goals}")
        logging.info(f"Trading Instruments: {self.trading_instruments}")
    
    def calculate_rsi(self, prices, period=14):
        """
        Calculate RSI (Relative Strength Index)
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_mean_reversion_signal(self, prices, lookback=20, threshold=2.0):
        """
        Calculate Mean Reversion Signal
        Signal based on how many standard deviations current price is from moving average
        """
        rolling_mean = prices.rolling(window=lookback).mean()
        rolling_std = prices.rolling(window=lookback).std()
        
        # Z-score calculation
        z_score = (prices - rolling_mean) / rolling_std
        
        return z_score, rolling_mean, rolling_std
    
    def get_historical_data_from_db(self, symbol, days=100):
        """Get historical data from our existing database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get recent data for analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            query = """
                SELECT timestamp, close, high, low, open, volume
                FROM market_data 
                WHERE symbol = ? 
                AND timestamp >= ? 
                AND timestamp <= ?
                ORDER BY timestamp ASC
            """
            
            df = pd.read_sql_query(query, conn, params=[symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
            conn.close()
            
            if not df.empty:
                # Handle different timestamp formats
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                except ValueError:
                    # Try different formats
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
                
                df.set_index('timestamp', inplace=True)
                
                logging.info(f"Retrieved {len(df)} records for {symbol}")
            
            return df
            
        except Exception as e:
            logging.error(f"Error retrieving historical data: {e}")
            return pd.DataFrame()
    
    def generate_trading_signals(self, symbol='SPY'):
        """
        Generate trading signals based on RSI + Mean Reversion
        Following assignment requirement for technical indicators
        """
        # Get historical data
        data = self.get_historical_data_from_db(symbol)
        
        if data.empty:
            logging.warning(f"No data available for {symbol}")
            return pd.DataFrame()
        
        # Calculate technical indicators
        data['rsi'] = self.calculate_rsi(data['close'], self.rsi_period)
        
        z_score, rolling_mean, rolling_std = self.calculate_mean_reversion_signal(
            data['close'], self.lookback_period, self.mean_reversion_threshold
        )
        
        data['z_score'] = z_score
        data['rolling_mean'] = rolling_mean
        data['rolling_std'] = rolling_std
        
        # Generate signals
        data['signal'] = 0
        
        # BUY Signal: RSI oversold AND price below mean (mean reversion opportunity)
        buy_condition = (data['rsi'] < self.rsi_oversold) & (data['z_score'] < -self.mean_reversion_threshold)
        data.loc[buy_condition, 'signal'] = 1
        
        # SELL Signal: RSI overbought AND price above mean (mean reversion opportunity)
        sell_condition = (data['rsi'] > self.rsi_overbought) & (data['z_score'] > self.mean_reversion_threshold)
        data.loc[sell_condition, 'signal'] = -1
        
        # Add signal strength
        data['signal_strength'] = abs(data['z_score']) * (100 - abs(data['rsi'] - 50)) / 50
        
        return data
    
    def backtest_strategy(self, symbol='SPY', initial_capital=10000):
        """
        4. BACKTESTING (Assignment Step 7.4)
        Backtest the trading strategy using historical data
        """
        logging.info(f"Starting backtest for {symbol}")
        
        # Get signals
        data = self.generate_trading_signals(symbol)
        
        if data.empty:
            logging.error("No data available for backtesting")
            return {}
        
        # Initialize backtesting variables
        capital = initial_capital
        position = 0  # 0: no position, 1: long, -1: short
        position_size = 0
        entry_price = 0
        trades = []
        equity_curve = []
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = row['close']
            signal = row['signal']
            
            # Calculate current portfolio value
            if position != 0:
                unrealized_pnl = (current_price - entry_price) * position * position_size
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'price': current_price,
                'rsi': row['rsi'],
                'z_score': row['z_score'],
                'signal': signal,
                'position': position
            })
            
            # Execute trades based on signals
            if signal == 1 and position <= 0:  # Buy signal
                if position < 0:  # Close short position first
                    pnl = (entry_price - current_price) * position_size
                    capital += pnl
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'cover',
                        'price': current_price,
                        'size': position_size,
                        'pnl': pnl
                    })
                
                # Open long position
                position_size = min(self.position_size, int(capital / current_price))
                if position_size > 0:
                    entry_price = current_price
                    position = 1
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'buy',
                        'price': current_price,
                        'size': position_size,
                        'pnl': 0
                    })
            
            elif signal == -1 and position >= 0:  # Sell signal
                if position > 0:  # Close long position first
                    pnl = (current_price - entry_price) * position_size
                    capital += pnl
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'sell',
                        'price': current_price,
                        'size': position_size,
                        'pnl': pnl
                    })
                
                # Open short position (if allowed)
                position_size = min(self.position_size, int(capital / current_price))
                if position_size > 0:
                    entry_price = current_price
                    position = -1
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'short',
                        'price': current_price,
                        'size': position_size,
                        'pnl': 0
                    })
        
        # Calculate final performance metrics
        if trades:
            total_trades = len([t for t in trades if t['action'] in ['buy', 'short']])
            profitable_trades = len([t for t in trades if t['pnl'] > 0])
            total_pnl = sum([t['pnl'] for t in trades])
            
            win_rate = profitable_trades / max(total_trades, 1) if total_trades > 0 else 0
            final_capital = capital + total_pnl
            total_return = (final_capital - initial_capital) / initial_capital
            
            backtest_results = {
                'initial_capital': initial_capital,
                'final_capital': final_capital,
                'total_return': total_return,
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'trades': trades,
                'equity_curve': equity_curve
            }
            
            logging.info(f"Backtest completed:")
            logging.info(f"  Total Return: {total_return:.2%}")
            logging.info(f"  Total Trades: {total_trades}")
            logging.info(f"  Win Rate: {win_rate:.2%}")
            
            return backtest_results
        
        else:
            logging.warning("No trades generated during backtesting period")
            return {'message': 'No trades generated'}
    
    def get_current_position(self):
        """Get current positions from Alpaca paper trading account"""
        try:
            positions = self.trading_client.get_all_positions()
            position_dict = {}
            for pos in positions:
                try:
                    position_dict[str(pos.symbol)] = float(pos.qty)
                except AttributeError:
                    logging.warning("Could not access position attributes")
            return position_dict
        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return {}
    
    def place_paper_trade(self, symbol, side, quantity):
        """
        5. PAPER TRADING (Assignment Step 7.5)
        Place trades in paper trading environment
        """
        try:
            if side.upper() == 'BUY':
                order_side = OrderSide.BUY
            else:
                order_side = OrderSide.SELL
            
            # Create market order
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.trading_client.submit_order(market_order_data)
            
            logging.info(f"Paper trade placed: {side} {quantity} shares of {symbol}")
            logging.info(f"Order submitted successfully")
            
            return order
            
        except Exception as e:
            logging.error(f"Error placing paper trade: {e}")
            return None
    
    def monitor_strategy_performance(self):
        """
        6. REAL-TIME MONITORING (Assignment Step 7.6)
        Monitor algorithm performance in real-time
        """
        try:
            # Get account information
            account = self.trading_client.get_account()
            
            # Get current positions
            positions = self.get_current_position()
            
            # Get recent orders
            orders = self.trading_client.get_orders()
            
            # Safe attribute access
            account_equity = getattr(account, 'equity', '0')
            buying_power = getattr(account, 'buying_power', '0')
            day_trade_count = getattr(account, 'daytrade_count', '0')
            
            performance_data = {
                'timestamp': datetime.now(),
                'account_equity': float(account_equity) if account_equity else 0.0,
                'buying_power': float(buying_power) if buying_power else 0.0,
                'day_trade_count': int(day_trade_count) if day_trade_count else 0,
                'positions': positions,
                'recent_orders': len(orders) if orders else 0
            }
            
            logging.info("Strategy Performance Monitor:")
            logging.info(f"  Account Equity: ${performance_data['account_equity']:,.2f}")
            logging.info(f"  Buying Power: ${performance_data['buying_power']:,.2f}")
            logging.info(f"  Active Positions: {len(positions)}")
            
            return performance_data
            
        except Exception as e:
            logging.error(f"Error monitoring performance: {e}")
            return {
                'timestamp': datetime.now(),
                'account_equity': 0.0,
                'buying_power': 0.0,
                'day_trade_count': 0,
                'positions': {},
                'recent_orders': 0,
                'error': str(e)
            }
    
    def run_strategy_analysis(self):
        """Run complete strategy analysis following assignment steps"""
        logging.info("=" * 60)
        logging.info("STEP 7: TRADING STRATEGY ANALYSIS")
        logging.info("=" * 60)
        
        # 1. Trading Goals (already defined in __init__)
        logging.info("1. TRADING GOALS:")
        for key, value in self.trading_goals.items():
            logging.info(f"   {key.replace('_', ' ').title()}: {value}")
        
        # 2. Trading Instruments
        logging.info(f"\n2. SELECTED TRADING INSTRUMENTS: {self.trading_instruments}")
        
        # 3. Technical Indicators (RSI + Mean Reversion)
        logging.info("\n3. TECHNICAL INDICATORS:")
        logging.info(f"   RSI Period: {self.rsi_period}")
        logging.info(f"   RSI Oversold/Overbought: {self.rsi_oversold}/{self.rsi_overbought}")
        logging.info(f"   Mean Reversion Period: {self.lookback_period}")
        logging.info(f"   Mean Reversion Threshold: {self.mean_reversion_threshold} std devs")
        
        # 4. Backtesting
        logging.info("\n4. BACKTESTING RESULTS:")
        backtest_results = self.backtest_strategy(self.primary_symbol)
        
        # 5. Paper Trading Status
        logging.info("\n5. PAPER TRADING STATUS:")
        performance = self.monitor_strategy_performance()
        
        return {
            'trading_goals': self.trading_goals,
            'instruments': self.trading_instruments,
            'backtest_results': backtest_results,
            'current_performance': performance
        }

def main():
    """Main function to run Step 7 trading strategy analysis"""
    strategy = RSIMeanReversionStrategy()
    results = strategy.run_strategy_analysis()
    
    print("\n" + "="*60)
    print("STEP 7: TRADING STRATEGY IMPLEMENTATION COMPLETE")
    print("="*60)
    
    if 'backtest_results' in results and 'total_return' in results['backtest_results']:
        print(f"Backtest Total Return: {results['backtest_results']['total_return']:.2%}")
        print(f"Win Rate: {results['backtest_results']['win_rate']:.2%}")
        print(f"Total Trades: {results['backtest_results']['total_trades']}")

if __name__ == "__main__":
    main()
