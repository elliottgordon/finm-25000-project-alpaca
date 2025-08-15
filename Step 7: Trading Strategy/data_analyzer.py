# Step 5: Data Analysis and Visualization Tool
# Comprehensive analysis of stored market data for insights and strategy development

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sqlite3
import logging
from pathlib import Path

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from data_management import MarketDataManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketDataAnalyzer:
    """
    Comprehensive market data analysis tool for Step 5 requirements.
    Provides statistical analysis, visualization, and insights for trading strategies.
    """
    
    def __init__(self):
        self.data_manager = MarketDataManager()
        self.analysis_dir = 'analysis_outputs'
        
        # Create analysis output directory
        if not os.path.exists(self.analysis_dir):
            os.makedirs(self.analysis_dir)
        
        # Set plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        logging.info("MarketDataAnalyzer initialized")
    
    def get_symbol_statistics(self, symbol, start_date=None, end_date=None):
        """Calculate comprehensive statistics for a specific symbol"""
        data = self.data_manager.get_data_from_database(
            symbols=symbol, start_date=start_date, end_date=end_date
        )
        
        if data.empty:
            logging.warning(f"No data found for symbol: {symbol}")
            return {}
        
        # Convert timestamp to datetime
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data = data.sort_values('timestamp')
        
        # Calculate returns
        data['daily_return'] = data['close'].pct_change()
        data['log_return'] = np.log(data['close'] / data['close'].shift(1))
        
        # Calculate volatility (rolling 30-day)
        data['volatility_30d'] = data['daily_return'].rolling(window=30).std() * np.sqrt(252)
        
        # Calculate moving averages
        data['ma_20'] = data['close'].rolling(window=20).mean()
        data['ma_50'] = data['close'].rolling(window=50).mean()
        data['ma_200'] = data['close'].rolling(window=200).mean()
        
        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate Bollinger Bands
        data['bb_middle'] = data['close'].rolling(window=20).mean()
        bb_std = data['close'].rolling(window=20).std()
        data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
        data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
        
        # Calculate statistics
        stats = {
            'symbol': symbol,
            'total_days': len(data),
            'date_range': {
                'start': data['timestamp'].min().strftime('%Y-%m-%d'),
                'end': data['timestamp'].max().strftime('%Y-%m-%d')
            },
            'price_stats': {
                'current_price': data['close'].iloc[-1],
                'highest_price': data['high'].max(),
                'lowest_price': data['low'].min(),
                'avg_price': data['close'].mean(),
                'price_change': data['close'].iloc[-1] - data['close'].iloc[0],
                'price_change_pct': ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
            },
            'volume_stats': {
                'avg_volume': data['volume'].mean(),
                'max_volume': data['volume'].max(),
                'volume_trend': 'Increasing' if data['volume'].iloc[-30:].mean() > data['volume'].iloc[-60:-30].mean() else 'Decreasing'
            },
            'volatility_stats': {
                'avg_daily_return': data['daily_return'].mean(),
                'volatility': data['daily_return'].std() * np.sqrt(252),
                'sharpe_ratio': (data['daily_return'].mean() * 252) / (data['daily_return'].std() * np.sqrt(252)) if data['daily_return'].std() > 0 else 0,
                'max_drawdown': self._calculate_max_drawdown(data['close'])
            },
            'technical_indicators': {
                'current_rsi': data['rsi'].iloc[-1],
                'rsi_status': 'Oversold' if data['rsi'].iloc[-1] < 30 else 'Overbought' if data['rsi'].iloc[-1] > 70 else 'Neutral',
                'ma_trend': 'Bullish' if data['ma_20'].iloc[-1] > data['ma_50'].iloc[-1] > data['ma_200'].iloc[-1] else 'Bearish' if data['ma_20'].iloc[-1] < data['ma_50'].iloc[-1] < data['ma_200'].iloc[-1] else 'Mixed'
            }
        }
        
        return stats, data
    
    def _calculate_max_drawdown(self, prices):
        """Calculate maximum drawdown from peak"""
        peak = prices.expanding(min_periods=1).max()
        drawdown = (prices - peak) / peak
        return drawdown.min() * 100
    
    def create_price_chart(self, symbol, start_date=None, end_date=None, save_plot=True):
        """Create comprehensive price chart with technical indicators"""
        stats, data = self.get_symbol_statistics(symbol, start_date, end_date)
        
        if data.empty:
            return False
        
        # Create figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Price chart with moving averages and Bollinger Bands
        ax1.plot(data['timestamp'], data['close'], label='Close Price', linewidth=2, color='black')
        ax1.plot(data['timestamp'], data['ma_20'], label='20-day MA', alpha=0.7, color='blue')
        ax1.plot(data['timestamp'], data['ma_50'], label='50-day MA', alpha=0.7, color='orange')
        ax1.plot(data['timestamp'], data['ma_200'], label='200-day MA', alpha=0.7, color='red')
        
        # Bollinger Bands
        ax1.fill_between(data['timestamp'], data['bb_lower'], data['bb_upper'], alpha=0.1, color='gray', label='Bollinger Bands')
        ax1.plot(data['timestamp'], data['bb_upper'], alpha=0.5, color='gray', linestyle='--')
        ax1.plot(data['timestamp'], data['bb_lower'], alpha=0.5, color='gray', linestyle='--')
        
        ax1.set_title(f'{symbol} Price Chart with Technical Indicators', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # Volume chart
        ax2.bar(data['timestamp'], data['volume'], alpha=0.7, color='lightblue', label='Volume')
        ax2.set_ylabel('Volume', fontsize=12)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)
        
        # RSI chart
        ax3.plot(data['timestamp'], data['rsi'], label='RSI', color='purple', linewidth=2)
        ax3.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Overbought (70)')
        ax3.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Oversold (30)')
        ax3.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='Neutral (50)')
        ax3.set_ylabel('RSI', fontsize=12)
        ax3.set_xlabel('Date', fontsize=12)
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 100)
        
        plt.tight_layout()
        
        if save_plot:
            filename = f"{symbol}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.analysis_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logging.info(f"Chart saved: {filepath}")
        
        plt.show()
        return True
    
    def create_correlation_matrix(self, symbols, start_date=None, end_date=None, save_plot=True):
        """Create correlation matrix for multiple symbols"""
        if len(symbols) < 2:
            logging.warning("Need at least 2 symbols for correlation analysis")
            return False
        
        # Get data for all symbols
        all_data = {}
        for symbol in symbols:
            data = self.data_manager.get_data_from_database(
                symbols=symbol, start_date=start_date, end_date=end_date
            )
            if not data.empty:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                data = data.set_index('timestamp')['close']
                all_data[symbol] = data
        
        if len(all_data) < 2:
            logging.warning("Insufficient data for correlation analysis")
            return False
        
        # Create DataFrame with all symbols
        df = pd.DataFrame(all_data)
        
        # Calculate returns and correlation
        returns = df.pct_change().dropna()
        correlation_matrix = returns.corr()
        
        # Create correlation heatmap
        plt.figure(figsize=(12, 10))
        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
        
        sns.heatmap(correlation_matrix, 
                   mask=mask,
                   annot=True, 
                   cmap='coolwarm', 
                   center=0,
                   square=True,
                   fmt='.2f',
                   cbar_kws={"shrink": .8})
        
        plt.title(f'Correlation Matrix: {", ".join(symbols)}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_plot:
            filename = f"correlation_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.analysis_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logging.info(f"Correlation matrix saved: {filepath}")
        
        plt.show()
        return correlation_matrix
    
    def create_portfolio_analysis(self, symbols, weights=None, start_date=None, end_date=None):
        """Analyze portfolio performance with given symbols and weights"""
        if weights is None:
            weights = [1/len(symbols)] * len(symbols)  # Equal weight
        
        if len(weights) != len(symbols):
            logging.error("Number of weights must match number of symbols")
            return {}
        
        # Get data for all symbols
        portfolio_data = {}
        for symbol in symbols:
            data = self.data_manager.get_data_from_database(
                symbols=symbol, start_date=start_date, end_date=end_date
            )
            if not data.empty:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                data = data.set_index('timestamp')['close']
                portfolio_data[symbol] = data
        
        if len(portfolio_data) < 2:
            logging.warning("Insufficient data for portfolio analysis")
            return {}
        
        # Create portfolio DataFrame
        df = pd.DataFrame(portfolio_data)
        returns = df.pct_change().dropna()
        
        # Calculate portfolio returns
        portfolio_returns = (returns * weights).sum(axis=1)
        
        # Calculate portfolio statistics
        portfolio_stats = {
            'total_return': (portfolio_returns + 1).prod() - 1,
            'annualized_return': (portfolio_returns + 1).prod() ** (252/len(portfolio_returns)) - 1,
            'volatility': portfolio_returns.std() * np.sqrt(252),
            'sharpe_ratio': portfolio_returns.mean() * 252 / (portfolio_returns.std() * np.sqrt(252)) if portfolio_returns.std() > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown((portfolio_returns + 1).cumprod()),
            'var_95': np.percentile(portfolio_returns, 5),
            'cvar_95': portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)].mean()
        }
        
        # Create portfolio performance chart
        cumulative_returns = (portfolio_returns + 1).cumprod()
        
        plt.figure(figsize=(15, 8))
        plt.plot(cumulative_returns.index, cumulative_returns.values, linewidth=2, color='blue', label='Portfolio')
        plt.title(f'Portfolio Performance: {", ".join(symbols)}', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Cumulative Return', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save plot
        filename = f"portfolio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.analysis_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logging.info(f"Portfolio analysis chart saved: {filepath}")
        
        plt.show()
        
        return portfolio_stats
    
    def generate_analysis_report(self, symbols, start_date=None, end_date=None, filename=None):
        """Generate comprehensive analysis report for multiple symbols"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_analysis_report_{timestamp}.json"
        
        report = {
            'analysis_date': datetime.now().isoformat(),
            'symbols_analyzed': symbols,
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'individual_analysis': {},
            'portfolio_analysis': None
        }
        
        # Individual symbol analysis
        for symbol in symbols:
            stats, _ = self.get_symbol_statistics(symbol, start_date, end_date)
            report['individual_analysis'][symbol] = stats
        
        # Portfolio analysis if multiple symbols
        if len(symbols) > 1:
            portfolio_stats = self.create_portfolio_analysis(symbols, start_date=start_date, end_date=end_date)
            report['portfolio_analysis'] = portfolio_stats
        
        # Save report
        filepath = os.path.join(self.analysis_dir, filename)
        with open(filepath, 'w') as f:
            import json
            json.dump(report, f, indent=2, default=str)
        
        logging.info(f"Analysis report saved: {filepath}")
        return report

def main():
    """Example usage and testing of MarketDataAnalyzer"""
    analyzer = MarketDataAnalyzer()
    
    # Example symbols to analyze
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    print("📊 MARKET DATA ANALYZER")
    print("=" * 50)
    print(f"Analyzing symbols: {', '.join(symbols)}")
    print()
    
    # Individual symbol analysis
    print("🔍 INDIVIDUAL SYMBOL ANALYSIS")
    print("=" * 50)
    
    for symbol in symbols[:2]:  # Analyze first 2 symbols
        print(f"\n📈 {symbol} Analysis:")
        stats, _ = analyzer.get_symbol_statistics(symbol, start_date='2025-01-01')
        
        if stats:
            print(f"  Current Price: ${stats['price_stats']['current_price']:.2f}")
            print(f"  YTD Change: {stats['price_stats']['price_change_pct']:.2f}%")
            print(f"  Volatility: {stats['volatility_stats']['volatility']:.2f}")
            print(f"  Sharpe Ratio: {stats['volatility_stats']['sharpe_ratio']:.2f}")
            print(f"  RSI: {stats['technical_indicators']['current_rsi']:.1f} ({stats['technical_indicators']['rsi_status']})")
            print(f"  Trend: {stats['technical_indicators']['ma_trend']}")
    
    # Create price chart for AAPL
    print(f"\n📊 Creating price chart for AAPL...")
    analyzer.create_price_chart('AAPL', start_date='2025-01-01')
    
    # Portfolio analysis
    print(f"\n💼 Creating portfolio analysis...")
    portfolio_stats = analyzer.create_portfolio_analysis(symbols, start_date='2025-01-01')
    
    if portfolio_stats:
        print(f"  Portfolio Return: {portfolio_stats['total_return']:.2%}")
        print(f"  Annualized Return: {portfolio_stats['annualized_return']:.2%}")
        print(f"  Volatility: {portfolio_stats['volatility']:.2%}")
        print(f"  Sharpe Ratio: {portfolio_stats['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {portfolio_stats['max_drawdown']:.2f}%")
    
    # Generate comprehensive report
    print(f"\n📋 Generating analysis report...")
    report = analyzer.generate_analysis_report(symbols, start_date='2025-01-01')
    print(f"✅ Analysis report generated: {report['analysis_date']}")

if __name__ == "__main__":
    main()
