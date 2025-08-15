# Step 7: Trading Strategy Analysis and Visualization
# Comprehensive analysis of RSI + Mean Reversion Strategy

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import sqlite3
from datetime import datetime, timedelta

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import our strategy
from trading_strategy import RSIMeanReversionStrategy

class StrategyAnalyzer:
    """
    Comprehensive analysis and visualization of the RSI Mean Reversion Strategy
    Following Step 7 assignment requirements with detailed analysis
    """
    
    def __init__(self):
        self.strategy = RSIMeanReversionStrategy()
        
    def get_full_historical_data(self, symbol='SPY', years=2):
        """Get more historical data for comprehensive analysis"""
        try:
            db_path = '../Step 5: Saving Market Data/market_data.db'
            conn = sqlite3.connect(db_path)
            
            # Get last 2 years of data for better analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years*365)
            
            query = """
                SELECT timestamp, close, high, low, open, volume
                FROM market_data 
                WHERE symbol = ? 
                AND date(timestamp) >= ? 
                AND date(timestamp) <= ?
                ORDER BY timestamp ASC
            """
            
            df = pd.read_sql_query(query, conn, params=[
                symbol, 
                start_date.strftime('%Y-%m-%d'), 
                end_date.strftime('%Y-%m-%d')
            ])
            conn.close()
            
            if not df.empty:
                # Handle timestamp parsing more robustly
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df = df.dropna(subset=['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                print(f"✅ Retrieved {len(df)} records for {symbol}")
                print(f"📅 Date range: {df.index.min()} to {df.index.max()}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error retrieving data: {e}")
            return pd.DataFrame()
    
    def analyze_strategy_performance(self, symbol='SPY'):
        """Comprehensive strategy performance analysis"""
        print("=" * 80)
        print("STEP 7: COMPREHENSIVE TRADING STRATEGY ANALYSIS")
        print("=" * 80)
        
        # Get historical data
        data = self.get_full_historical_data(symbol)
        
        if data.empty:
            print("❌ No data available for analysis")
            return None
            
        # Calculate technical indicators
        print(f"\n📊 Calculating Technical Indicators for {symbol}...")
        
        # RSI Calculation
        data['rsi'] = self.strategy.calculate_rsi(data['close'])
        
        # Mean Reversion Calculation  
        z_score, rolling_mean, rolling_std = self.strategy.calculate_mean_reversion_signal(
            data['close'], self.strategy.lookback_period, self.strategy.mean_reversion_threshold
        )
        data['z_score'] = z_score
        data['rolling_mean'] = rolling_mean
        data['rolling_std'] = rolling_std
        
        # Generate signals
        print("📡 Generating Trading Signals...")
        data['signal'] = 0
        
        # BUY signals: RSI oversold AND price significantly below mean
        buy_condition = (data['rsi'] < self.strategy.rsi_oversold) & (data['z_score'] < -self.strategy.mean_reversion_threshold)
        data.loc[buy_condition, 'signal'] = 1
        
        # SELL signals: RSI overbought AND price significantly above mean
        sell_condition = (data['rsi'] > self.strategy.rsi_overbought) & (data['z_score'] > self.strategy.mean_reversion_threshold)
        data.loc[sell_condition, 'signal'] = -1
        
        # Calculate signal statistics
        total_signals = (data['signal'] != 0).sum()
        buy_signals = (data['signal'] == 1).sum()
        sell_signals = (data['signal'] == -1).sum()
        
        print(f"📈 Signal Statistics:")
        print(f"   Total Signals: {total_signals}")
        print(f"   Buy Signals: {buy_signals}")
        print(f"   Sell Signals: {sell_signals}")
        
        # Run backtesting with the full dataset
        print(f"\n🔄 Running Backtesting Analysis...")
        backtest_results = self.run_custom_backtest(data)
        
        return data, backtest_results
    
    def run_custom_backtest(self, data, initial_capital=10000):
        """Custom backtesting with detailed analysis"""
        if data.empty:
            return {}
        
        # Initialize variables
        capital = initial_capital
        position = 0  # 0: no position, 1: long, -1: short
        position_size = 0
        entry_price = 0
        trades = []
        equity_curve = []
        max_equity = initial_capital
        max_drawdown = 0
        
        print(f"📊 Backtesting from {data.index[0].date()} to {data.index[-1].date()}")
        
        for timestamp, row in data.iterrows():
            current_price = row['close']
            signal = row['signal']
            
            # Calculate current equity
            if position != 0:
                unrealized_pnl = (current_price - entry_price) * position * position_size
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            # Track drawdown
            if current_equity > max_equity:
                max_equity = current_equity
            current_drawdown = (max_equity - current_equity) / max_equity
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
            
            equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'price': current_price,
                'rsi': row['rsi'],
                'z_score': row['z_score'],
                'signal': signal,
                'position': position
            })
            
            # Execute trades
            if signal == 1 and position <= 0:  # Buy signal
                if position < 0:  # Close short first
                    pnl = (entry_price - current_price) * position_size
                    capital += pnl
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'cover',
                        'price': current_price,
                        'size': position_size,
                        'pnl': pnl,
                        'rsi': row['rsi'],
                        'z_score': row['z_score']
                    })
                
                # Open long position
                position_size = min(100, int(capital / current_price))
                if position_size > 0:
                    entry_price = current_price
                    position = 1
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'buy',
                        'price': current_price,
                        'size': position_size,
                        'pnl': 0,
                        'rsi': row['rsi'],
                        'z_score': row['z_score']
                    })
            
            elif signal == -1 and position >= 0:  # Sell signal
                if position > 0:  # Close long first
                    pnl = (current_price - entry_price) * position_size
                    capital += pnl
                    trades.append({
                        'timestamp': timestamp,
                        'action': 'sell',
                        'price': current_price,
                        'size': position_size,
                        'pnl': pnl,
                        'rsi': row['rsi'],
                        'z_score': row['z_score']
                    })
                    position = 0
                    position_size = 0
        
        # Calculate performance metrics
        if trades:
            total_trades = len([t for t in trades if t['action'] in ['buy', 'short']])
            profitable_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = len([t for t in trades if t['pnl'] < 0])
            total_pnl = sum([t['pnl'] for t in trades])
            
            if profitable_trades > 0:
                avg_win = sum([t['pnl'] for t in trades if t['pnl'] > 0]) / profitable_trades
            else:
                avg_win = 0
                
            if losing_trades > 0:
                avg_loss = sum([t['pnl'] for t in trades if t['pnl'] < 0]) / losing_trades
            else:
                avg_loss = 0
            
            win_rate = profitable_trades / max(total_trades, 1)
            final_capital = capital + total_pnl
            total_return = (final_capital - initial_capital) / initial_capital
            
            # Calculate Sharpe ratio (simplified)
            if len(equity_curve) > 1:
                returns = pd.Series([eq['equity'] for eq in equity_curve]).pct_change().dropna()
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            else:
                sharpe_ratio = 0
            
            results = {
                'initial_capital': initial_capital,
                'final_capital': final_capital,
                'total_return': total_return,
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'trades': trades,
                'equity_curve': equity_curve
            }
            
            # Print results
            print(f"\n🎯 BACKTESTING RESULTS:")
            print(f"   Initial Capital: ${initial_capital:,.2f}")
            print(f"   Final Capital: ${final_capital:,.2f}")
            print(f"   Total Return: {total_return:.2%}")
            print(f"   Total Trades: {total_trades}")
            print(f"   Win Rate: {win_rate:.2%}")
            print(f"   Average Win: ${avg_win:.2f}")
            print(f"   Average Loss: ${avg_loss:.2f}")
            print(f"   Max Drawdown: {max_drawdown:.2%}")
            print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
            
            return results
        else:
            print("⚠️  No trades generated in backtesting period")
            return {'message': 'No trades generated'}
    
    def create_strategy_visualization(self, data, backtest_results, symbol='SPY'):
        """Create comprehensive strategy visualization"""
        if data.empty:
            return
        
        print(f"\n📈 Creating Strategy Visualization for {symbol}...")
        
        fig, axes = plt.subplots(4, 1, figsize=(15, 12))
        fig.suptitle(f'RSI + Mean Reversion Strategy Analysis - {symbol}', fontsize=16, fontweight='bold')
        
        # 1. Price and signals
        ax1 = axes[0]
        ax1.plot(data.index, data['close'], label='Close Price', linewidth=1)
        ax1.plot(data.index, data['rolling_mean'], label='20-Day Mean', alpha=0.7)
        
        # Mark buy/sell signals
        buy_signals = data[data['signal'] == 1]
        sell_signals = data[data['signal'] == -1]
        
        ax1.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', s=100, label='Buy Signal', zorder=5)
        ax1.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', s=100, label='Sell Signal', zorder=5)
        
        ax1.set_title('Price Action with Trading Signals')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. RSI
        ax2 = axes[1]
        ax2.plot(data.index, data['rsi'], label='RSI', color='purple')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Overbought (70)')
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Oversold (30)')
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='Neutral (50)')
        ax2.fill_between(data.index, 30, 70, alpha=0.1, color='gray')
        ax2.set_title('RSI (14-period)')
        ax2.set_ylabel('RSI')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 100)
        
        # 3. Z-Score (Mean Reversion)
        ax3 = axes[2]
        ax3.plot(data.index, data['z_score'], label='Z-Score', color='orange')
        ax3.axhline(y=2, color='r', linestyle='--', alpha=0.7, label='Upper Threshold (+2σ)')
        ax3.axhline(y=-2, color='g', linestyle='--', alpha=0.7, label='Lower Threshold (-2σ)')
        ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax3.fill_between(data.index, -2, 2, alpha=0.1, color='gray')
        ax3.set_title('Mean Reversion Z-Score (20-period)')
        ax3.set_ylabel('Z-Score')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Equity curve
        if backtest_results and 'equity_curve' in backtest_results:
            equity_data = pd.DataFrame(backtest_results['equity_curve'])
            ax4 = axes[3]
            ax4.plot(equity_data['timestamp'], equity_data['equity'], label='Strategy Equity', color='blue', linewidth=2)
            ax4.axhline(y=backtest_results['initial_capital'], color='gray', linestyle='--', alpha=0.7, label='Initial Capital')
            ax4.set_title('Strategy Equity Curve')
            ax4.set_ylabel('Portfolio Value ($)')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            # Format y-axis as currency
            ax4.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        
        # Save the plot
        filename = f'strategy_analysis_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"📊 Strategy visualization saved as: {filename}")
        
        plt.show()

def main():
    """Main function to run comprehensive Step 7 analysis"""
    analyzer = StrategyAnalyzer()
    
    print("🚀 Starting Step 7: Trading Strategy Comprehensive Analysis")
    print("Strategy: RSI + Mean Reversion")
    print("Assets: SPY (S&P 500 ETF)")
    
    # Run analysis
    result = analyzer.analyze_strategy_performance('SPY')
    
    if result is not None:
        data, backtest_results = result
    
    if data is not None and not data.empty:
        # Create visualizations
        analyzer.create_strategy_visualization(data, backtest_results, 'SPY')
        
        print("\n" + "=" * 80)
        print("✅ STEP 7: TRADING STRATEGY ANALYSIS COMPLETE")
        print("=" * 80)
        print("📋 Summary:")
        print("   1. ✅ Trading Goals Defined")
        print("   2. ✅ Trading Instruments Selected (SPY, VXX)")
        print("   3. ✅ Technical Indicators Implemented (RSI + Mean Reversion)")
        print("   4. ✅ Backtesting Completed")
        print("   5. ✅ Paper Trading Integration Ready")
        print("   6. ✅ Real-time Monitoring Implemented")
        print("\n📊 Strategy ready for deployment in paper trading environment!")
    else:
        print("❌ Analysis could not be completed due to data issues")

if __name__ == "__main__":
    main()
