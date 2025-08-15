# Multi-Asset Portfolio Strategy
# Implements RSI + Mean Reversion across top-ranked assets
# Manages position sizing, risk allocation, and portfolio-level controls

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from trading_strategy import RSIMeanReversionStrategy

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class MultiAssetPortfolioStrategy:
    """
    Multi-asset implementation of RSI + Mean Reversion strategy
    Manages portfolio allocation across top-performing assets
    """
    
    def __init__(self, 
                 initial_capital: float = 1_000_000,
                 max_positions: int = 8,
                 position_size_pct: float = 0.10,
                 db_path: str = '../Step 5: Saving Market Data/market_data.db'):
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.db_path = db_path
        
        # Strategy instance
        self.strategy = RSIMeanReversionStrategy()
        
        # Portfolio tracking
        self.positions = {}  # symbol -> position info
        self.portfolio_history = []
        self.trade_log = []
        
        # Top assets from screening (hardcoded from results)
        self.top_assets = [
            'XLI',  # Industrial ETF - Score 95.0
            'EFA',  # EAFE ETF - Score 95.0  
            'VWO',  # Emerging Markets ETF - Score 95.0
            'XLK',  # Technology ETF - Score 95.0
            'EEM',  # Emerging Markets ETF - Score 95.0
            'DIA',  # Dow ETF - Score 90.0
            'VEA',  # Developed Markets ETF - Score 90.0
            'VTI',  # Total Stock Market ETF - Score 90.0
        ]
        
        logging.info(f"Multi-Asset Portfolio Strategy initialized")
        logging.info(f"Capital: ${initial_capital:,.0f}, Max Positions: {max_positions}")
        logging.info(f"Position Size: {position_size_pct:.1%}, Top Assets: {len(self.top_assets)}")
    
    def get_asset_data(self, symbol: str, days: int = 500) -> pd.DataFrame:
        """Get historical data for an asset"""
        conn = sqlite3.connect(self.db_path)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = """
            SELECT timestamp, close, high, low, open, volume
            FROM market_data 
            WHERE symbol = ? 
            AND date(timestamp) >= date(?) 
            AND date(timestamp) <= date(?)
            ORDER BY timestamp ASC
        """
        
        df = pd.read_sql_query(query, conn, params=[
            symbol, 
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d')
        ])
        
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        return df
    
    def calculate_signals(self, data: pd.DataFrame) -> Dict:
        """Calculate trading signals for asset data"""
        if data.empty or len(data) < 50:
            return {'buy_signal': False, 'sell_signal': False, 'strength': 0}
        
        try:
            # Calculate indicators
            rsi = self.strategy.calculate_rsi(data['close'])
            z_score, rolling_mean, rolling_std = self.strategy.calculate_mean_reversion_signal(data['close'])
            
            # Get latest values
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            current_z_score = z_score.iloc[-1] if not z_score.empty else 0
            current_price = data['close'].iloc[-1]
            
            # Signal generation
            buy_signal = (current_rsi < 30) and (current_z_score < -2.0)
            sell_signal = (current_rsi > 70) and (current_z_score > 2.0)
            
            # Signal strength (0-100)
            strength = 0
            if buy_signal:
                strength = min(100, (30 - current_rsi) * 2 + abs(current_z_score) * 10)
            elif sell_signal:
                strength = min(100, (current_rsi - 70) * 2 + abs(current_z_score) * 10)
            
            return {
                'buy_signal': buy_signal,
                'sell_signal': sell_signal,
                'strength': strength,
                'rsi': current_rsi,
                'z_score': current_z_score,
                'price': current_price
            }
            
        except Exception as e:
            logging.error(f"Error calculating signals: {str(e)}")
            return {'buy_signal': False, 'sell_signal': False, 'strength': 0}
    
    def calculate_position_size(self, symbol: str, price: float, signal_strength: float) -> int:
        """Calculate position size based on capital and signal strength"""
        base_allocation = self.current_capital * self.position_size_pct
        
        # Adjust for signal strength (50-150% of base allocation)
        strength_multiplier = 0.5 + (signal_strength / 100)
        adjusted_allocation = base_allocation * strength_multiplier
        
        # Calculate shares (rounded down)
        shares = int(adjusted_allocation / price)
        
        return max(0, shares)
    
    def execute_trade(self, symbol: str, action: str, shares: int, price: float, 
                     timestamp: datetime, signal_info: Dict) -> Dict:
        """Execute a trade and update portfolio"""
        trade_value = shares * price
        
        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'action': action,
            'shares': shares,
            'price': price,
            'value': trade_value,
            'rsi': signal_info.get('rsi', 0),
            'z_score': signal_info.get('z_score', 0),
            'signal_strength': signal_info.get('strength', 0),
            'portfolio_value_before': self.current_capital
        }
        
        if action == 'BUY':
            if symbol not in self.positions:
                self.positions[symbol] = {'shares': 0, 'avg_price': 0, 'total_cost': 0}
            
            # Update position
            old_shares = self.positions[symbol]['shares']
            old_cost = self.positions[symbol]['total_cost']
            
            new_shares = old_shares + shares
            new_cost = old_cost + trade_value
            
            self.positions[symbol] = {
                'shares': new_shares,
                'avg_price': new_cost / new_shares if new_shares > 0 else 0,
                'total_cost': new_cost
            }
            
            self.current_capital -= trade_value
            
        elif action == 'SELL':
            if symbol in self.positions and self.positions[symbol]['shares'] >= shares:
                # Update position
                self.positions[symbol]['shares'] -= shares
                self.positions[symbol]['total_cost'] -= (self.positions[symbol]['avg_price'] * shares)
                
                if self.positions[symbol]['shares'] == 0:
                    del self.positions[symbol]
                
                self.current_capital += trade_value
            else:
                logging.warning(f"Cannot sell {shares} shares of {symbol} - insufficient position")
                return {}
        
        trade['portfolio_value_after'] = self.current_capital
        self.trade_log.append(trade)
        
        logging.info(f"{action} {shares} {symbol} @ ${price:.2f} (Strength: {signal_info.get('strength', 0):.1f})")
        
        return trade
    
    def get_portfolio_value(self, date: datetime) -> float:
        """Calculate total portfolio value"""
        cash = self.current_capital
        positions_value = 0
        
        for symbol, position in self.positions.items():
            try:
                # Get current price (use latest available)
                data = self.get_asset_data(symbol, days=5)
                if not data.empty:
                    current_price = data['close'].iloc[-1]
                    positions_value += position['shares'] * current_price
            except:
                # Use average price if current price unavailable
                positions_value += position['shares'] * position['avg_price']
        
        return cash + positions_value
    
    def run_backtest(self, start_date: str = '2023-01-01', end_date: str = '2025-08-01') -> Dict:
        """Run multi-asset portfolio backtest"""
        logging.info(f"Starting multi-asset backtest from {start_date} to {end_date}")
        
        # Reset portfolio
        self.current_capital = self.initial_capital
        self.positions = {}
        self.portfolio_history = []
        self.trade_log = []
        
        # Get date range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Create trading calendar (business days)
        trading_dates = pd.bdate_range(start=start_dt, end=end_dt)
        
        # Track daily portfolio values
        daily_values = []
        debug_days = 0
        
        for date in trading_dates:
            debug_days += 1
            if debug_days % 50 == 0:  # Log progress every 50 days
                logging.info(f"Processing day {debug_days}/{len(trading_dates)}: {date.strftime('%Y-%m-%d')}")
            
            date_str = date.strftime('%Y-%m-%d')
            
            # Check each top asset for signals
            signals_today = []
            
            for symbol in self.top_assets:
                try:
                    # Get data up to current date
                    data = self.get_asset_data(symbol, days=252)
                    
                    if data.empty:
                        continue
                    
                    # Filter data up to current date
                    data_filtered = data[data.index <= date]
                    
                    if len(data_filtered) < 50:
                        continue
                    
                    # Calculate signals
                    signal_info = self.calculate_signals(data_filtered)
                    
                    if signal_info['buy_signal'] or signal_info['sell_signal']:
                        signals_today.append({
                            'symbol': symbol,
                            'signal_info': signal_info,
                            'data': data_filtered
                        })
                
                except Exception as e:
                    logging.debug(f"Error processing {symbol} on {date_str}: {str(e)}")
                    continue
            
            # Process signals (sort by strength)
            signals_today.sort(key=lambda x: x['signal_info']['strength'], reverse=True)
            
            for signal in signals_today:
                symbol = signal['symbol']
                signal_info = signal['signal_info']
                current_price = signal_info['price']
                
                # Buy signals
                if signal_info['buy_signal'] and len(self.positions) < self.max_positions:
                    if symbol not in self.positions:
                        shares = self.calculate_position_size(symbol, current_price, signal_info['strength'])
                        if shares > 0 and shares * current_price <= self.current_capital * 0.9:  # Keep 10% cash buffer
                            self.execute_trade(symbol, 'BUY', shares, current_price, date, signal_info)
                
                # Sell signals
                elif signal_info['sell_signal'] and symbol in self.positions:
                    shares_to_sell = self.positions[symbol]['shares']
                    if shares_to_sell > 0:
                        self.execute_trade(symbol, 'SELL', shares_to_sell, current_price, date, signal_info)
            
            # Record daily portfolio value
            portfolio_value = self.get_portfolio_value(date)
            daily_values.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.current_capital,
                'positions_count': len(self.positions),
                'positions_value': portfolio_value - self.current_capital
            })
        
        self.portfolio_history = daily_values
        
        # Calculate performance metrics
        performance = self.calculate_performance_metrics()
        
        logging.info(f"Backtest complete. Final value: ${performance['final_value']:,.0f}")
        logging.info(f"Total return: {performance['total_return']:.1%}")
        logging.info(f"Total trades: {len(self.trade_log)}")
        
        return performance
    
    def calculate_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.portfolio_history:
            return {}
        
        # Convert to DataFrame
        df = pd.DataFrame(self.portfolio_history)
        df.set_index('date', inplace=True)
        
        # Calculate returns
        df['daily_return'] = df['portfolio_value'].pct_change()
        
        # Basic metrics
        final_value = df['portfolio_value'].iloc[-1]
        total_return = (final_value / self.initial_capital) - 1
        
        # Risk metrics
        volatility = df['daily_return'].std() * np.sqrt(252)
        sharpe_ratio = df['daily_return'].mean() / df['daily_return'].std() * np.sqrt(252) if df['daily_return'].std() > 0 else 0
        
        # Drawdown
        running_max = df['portfolio_value'].expanding().max()
        drawdown = (df['portfolio_value'] - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # Trade analysis
        trades_df = pd.DataFrame(self.trade_log) if self.trade_log else pd.DataFrame()
        
        buy_trades = len(trades_df[trades_df['action'] == 'BUY']) if not trades_df.empty else 0
        sell_trades = len(trades_df[trades_df['action'] == 'SELL']) if not trades_df.empty else 0
        
        return {
            'initial_value': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'annualized_return': (1 + total_return) ** (252 / len(df)) - 1,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': len(trades_df),
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'avg_positions': df['positions_count'].mean(),
            'max_positions': df['positions_count'].max(),
            'final_positions': len(self.positions),
            'final_cash_pct': self.current_capital / final_value if final_value > 0 else 0
        }
    
    def create_performance_report(self, performance: Dict):
        """Create comprehensive performance report"""
        print("=" * 80)
        print("MULTI-ASSET PORTFOLIO STRATEGY PERFORMANCE REPORT")
        print("=" * 80)
        
        print(f"\n💰 PORTFOLIO PERFORMANCE")
        print(f"   Initial Capital: ${performance['initial_value']:,.0f}")
        print(f"   Final Value: ${performance['final_value']:,.0f}")
        print(f"   Total Return: {performance['total_return']:+.1%}")
        print(f"   Annualized Return: {performance['annualized_return']:+.1%}")
        
        print(f"\n📊 RISK METRICS")
        print(f"   Volatility: {performance['volatility']:.1%}")
        print(f"   Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        print(f"   Maximum Drawdown: {performance['max_drawdown']:.1%}")
        
        print(f"\n🔄 TRADING ACTIVITY")
        print(f"   Total Trades: {performance['total_trades']}")
        print(f"   Buy Trades: {performance['buy_trades']}")
        print(f"   Sell Trades: {performance['sell_trades']}")
        
        print(f"\n📈 POSITION MANAGEMENT")
        print(f"   Average Positions: {performance['avg_positions']:.1f}")
        print(f"   Maximum Positions: {performance['max_positions']}")
        print(f"   Final Positions: {performance['final_positions']}")
        print(f"   Final Cash %: {performance['final_cash_pct']:.1%}")
        
        # Top performing assets
        if self.trade_log:
            trades_df = pd.DataFrame(self.trade_log)
            symbol_performance = trades_df.groupby('symbol').agg({
                'action': 'count',
                'value': 'sum'
            }).rename(columns={'action': 'trades', 'value': 'total_volume'})
            symbol_performance = symbol_performance.sort_values('total_volume', ascending=False)
            
            print(f"\n🏆 TOP TRADING ASSETS")
            for symbol, row in symbol_performance.head(8).iterrows():
                print(f"   {symbol}: {row['trades']} trades, ${row['total_volume']:,.0f} volume")

def main():
    """Run multi-asset portfolio strategy"""
    print("🚀 Multi-Asset Portfolio Strategy - RSI + Mean Reversion")
    print("=" * 70)
    
    # Initialize strategy
    portfolio_strategy = MultiAssetPortfolioStrategy(
        initial_capital=1_000_000,
        max_positions=8,
        position_size_pct=0.12  # 12% per position
    )
    
    # Run backtest
    performance = portfolio_strategy.run_backtest(
        start_date='2023-01-01',
        end_date='2025-08-01'  # Extended to include more recent data
    )
    
    # Create report
    portfolio_strategy.create_performance_report(performance)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save trade log
    if portfolio_strategy.trade_log:
        trades_df = pd.DataFrame(portfolio_strategy.trade_log)
        trades_filename = f'multi_asset_trades_{timestamp}.csv'
        trades_df.to_csv(trades_filename, index=False)
        print(f"\n💾 Trade log saved as: {trades_filename}")
    
    # Save portfolio history
    if portfolio_strategy.portfolio_history:
        portfolio_df = pd.DataFrame(portfolio_strategy.portfolio_history)
        portfolio_filename = f'multi_asset_portfolio_{timestamp}.csv'
        portfolio_df.to_csv(portfolio_filename, index=False)
        print(f"💾 Portfolio history saved as: {portfolio_filename}")
    
    print(f"\n✅ Multi-asset strategy analysis complete!")

if __name__ == "__main__":
    main()
