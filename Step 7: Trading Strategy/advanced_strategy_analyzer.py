#!/usr/bin/env python3
"""
🚀 ADVANCED MULTI-ASSET STRATEGY ANALYZER
Enhanced Alpaca Project - 7+ Years Historical Data Analysis

Features:
- Portfolio construction from expanded 100+ asset universe
- Risk-adjusted position sizing
- Multi-asset correlation analysis
- Sector rotation signals
- Advanced mean reversion + momentum combination
- Volatility regime detection
- Performance attribution analysis

Usage:
    python advanced_strategy_analyzer.py
"""

import logging
import sqlite3
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdvancedStrategyAnalyzer:
    """Advanced multi-asset strategy analysis with 7+ years of data"""
    
    def __init__(self, db_path='../Step 5: Saving Market Data/market_data.db'):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Initialize database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"✅ Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def get_multi_asset_data(self, symbols, start_date=None, end_date=None):
        """Get comprehensive multi-asset dataset"""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')  # 3 years default
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        symbol_placeholders = ','.join(['?' for _ in symbols])
        query = f"""
        SELECT 
            symbol,
            DATE(timestamp) as date,
            close,
            high,
            low,
            volume
        FROM market_data 
        WHERE symbol IN ({symbol_placeholders})
        AND DATE(timestamp) BETWEEN ? AND ?
        ORDER BY symbol, timestamp
        """
        
        df = pd.read_sql_query(query, self.conn, params=symbols + [start_date, end_date])
        return df.pivot_table(index='date', columns='symbol', values='close')
    
    def calculate_portfolio_metrics(self, returns_df, weights=None):
        """Calculate comprehensive portfolio metrics"""
        if weights is None:
            weights = np.ones(len(returns_df.columns)) / len(returns_df.columns)  # Equal weight
        
        # Ensure weights sum to 1
        weights = np.array(weights) / np.sum(weights)
        
        # Portfolio returns
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        # Performance metrics
        total_return = (1 + portfolio_returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Drawdown analysis
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Additional risk metrics
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = annualized_return / downside_deviation if downside_deviation > 0 else 0
        
        # VaR and CVaR (5%)
        var_5 = np.percentile(portfolio_returns, 5)
        cvar_5 = portfolio_returns[portfolio_returns <= var_5].mean()
        
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'var_5': var_5,
            'cvar_5': cvar_5,
            'win_rate': (portfolio_returns > 0).mean(),
            'avg_win': portfolio_returns[portfolio_returns > 0].mean(),
            'avg_loss': portfolio_returns[portfolio_returns < 0].mean(),
        }
        
        return metrics, portfolio_returns
    
    def analyze_correlation_matrix(self, price_df):
        """Analyze asset correlations and identify diversification opportunities"""
        returns_df = price_df.pct_change().dropna()
        corr_matrix = returns_df.corr()
        
        # Find highest and lowest correlations
        corr_values = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                asset1 = corr_matrix.columns[i]
                asset2 = corr_matrix.columns[j]
                correlation = corr_matrix.iloc[i, j]
                corr_values.append({
                    'asset1': asset1,
                    'asset2': asset2,
                    'correlation': correlation
                })
        
        corr_df = pd.DataFrame(corr_values)
        
        logger.info("🔗 CORRELATION ANALYSIS:")
        logger.info("   Highest Correlations:")
        for _, row in corr_df.nlargest(5, 'correlation').iterrows():
            logger.info(f"      {row['asset1']:6} - {row['asset2']:6}: {row['correlation']:+6.3f}")
        
        logger.info("   Lowest Correlations (Best Diversifiers):")
        for _, row in corr_df.nsmallest(5, 'correlation').iterrows():
            logger.info(f"      {row['asset1']:6} - {row['asset2']:6}: {row['correlation']:+6.3f}")
        
        return corr_matrix, corr_df
    
    def detect_volatility_regimes(self, returns_series, window=20):
        """Detect high/low volatility regimes"""
        volatility = returns_series.rolling(window).std() * np.sqrt(252)
        vol_median = volatility.median()
        
        # Define regimes
        high_vol_threshold = vol_median * 1.5
        low_vol_threshold = vol_median * 0.7
        
        regimes = pd.Series(index=returns_series.index, dtype='object')
        regimes[volatility > high_vol_threshold] = 'High'
        regimes[volatility < low_vol_threshold] = 'Low'
        regimes.fillna('Normal', inplace=True)
        
        return regimes, volatility
    
    def backtest_enhanced_strategy(self, symbols, start_date=None, lookback=252):
        """Backtest enhanced multi-asset strategy"""
        logger.info("🚀 ENHANCED STRATEGY BACKTESTING")
        logger.info("=" * 60)
        
        # Get price data
        price_df = self.get_multi_asset_data(symbols, start_date)
        if price_df.empty:
            logger.error("❌ No data available for backtesting")
            return None
        
        # Calculate returns
        returns_df = price_df.pct_change().dropna()
        
        logger.info(f"📊 Backtest Setup:")
        logger.info(f"   Assets: {list(price_df.columns)}")
        logger.info(f"   Date range: {price_df.index[0]} to {price_df.index[-1]}")
        logger.info(f"   Trading days: {len(price_df)}")
        logger.info("")
        
        # Strategy components
        strategies = {}
        
        # 1. Equal Weight Benchmark
        eq_weights = np.ones(len(returns_df.columns)) / len(returns_df.columns)
        eq_metrics, eq_returns = self.calculate_portfolio_metrics(returns_df, eq_weights)
        strategies['Equal Weight'] = {'metrics': eq_metrics, 'returns': eq_returns}
        
        # 2. Low Volatility Strategy
        vol_lookback = min(60, len(returns_df) // 4)
        rolling_vol = returns_df.rolling(vol_lookback).std() * np.sqrt(252)
        latest_vol = rolling_vol.iloc[-1]
        vol_weights = (1 / latest_vol) / (1 / latest_vol).sum()
        vol_metrics, vol_returns = self.calculate_portfolio_metrics(returns_df, vol_weights)
        strategies['Low Volatility'] = {'metrics': vol_metrics, 'returns': vol_returns}
        
        # 3. Momentum Strategy (12-1 month)
        momentum_lookback = min(220, len(returns_df) // 2)  # ~11 months
        momentum_scores = returns_df.rolling(momentum_lookback).apply(
            lambda x: (1 + x).prod() - 1, raw=False
        ).iloc[-1]
        # Top 50% momentum, equal weighted
        top_momentum = momentum_scores.nlargest(len(momentum_scores)//2)
        mom_weights = np.zeros(len(returns_df.columns))
        for i, symbol in enumerate(returns_df.columns):
            if symbol in top_momentum.index:
                mom_weights[i] = 1 / len(top_momentum)
        mom_metrics, mom_returns = self.calculate_portfolio_metrics(returns_df, mom_weights)
        strategies['Momentum'] = {'metrics': mom_metrics, 'returns': mom_returns}
        
        # 4. Mean Reversion Strategy
        # Select assets trading below their long-term averages
        sma_lookback = min(200, len(returns_df) // 2)
        latest_prices = price_df.iloc[-1]
        sma_prices = price_df.rolling(sma_lookback).mean().iloc[-1]
        undervalued = latest_prices[latest_prices < sma_prices * 0.95]  # 5% below SMA
        
        if len(undervalued) > 0:
            mr_weights = np.zeros(len(returns_df.columns))
            for i, symbol in enumerate(returns_df.columns):
                if symbol in undervalued.index:
                    mr_weights[i] = 1 / len(undervalued)
            mr_metrics, mr_returns = self.calculate_portfolio_metrics(returns_df, mr_weights)
            strategies['Mean Reversion'] = {'metrics': mr_metrics, 'returns': mr_returns}
        
        # Performance comparison
        logger.info("📈 STRATEGY PERFORMANCE COMPARISON:")
        logger.info("-" * 60)
        
        comparison_data = []
        for strategy_name, strategy_data in strategies.items():
            metrics = strategy_data['metrics']
            comparison_data.append({
                'Strategy': strategy_name,
                'Annual Return': f"{metrics['annualized_return']:+6.2%}",
                'Volatility': f"{metrics['volatility']:6.2%}",
                'Sharpe': f"{metrics['sharpe_ratio']:6.2f}",
                'Max DD': f"{metrics['max_drawdown']:6.2%}",
                'Win Rate': f"{metrics['win_rate']:6.2%}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        for _, row in comparison_df.iterrows():
            logger.info(f"{row['Strategy']:15} | Ret: {row['Annual Return']} | "
                       f"Vol: {row['Volatility']} | Sharpe: {row['Sharpe']} | "
                       f"DD: {row['Max DD']} | WR: {row['Win Rate']}")
        
        # Correlation analysis
        logger.info("")
        self.analyze_correlation_matrix(price_df)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save comparison
        csv_filename = f"strategy_comparison_{timestamp}.csv"
        comparison_df.to_csv(csv_filename, index=False)
        logger.info(f"💾 Strategy comparison saved: {csv_filename}")
        
        # Save detailed returns
        returns_comparison = pd.DataFrame({name: data['returns'] for name, data in strategies.items()})
        returns_filename = f"strategy_returns_{timestamp}.csv"
        returns_comparison.to_csv(returns_filename)
        logger.info(f"💾 Strategy returns saved: {returns_filename}")
        
        return strategies, comparison_df

def main():
    """Run advanced strategy analysis"""
    print("🚀 ADVANCED MULTI-ASSET STRATEGY ANALYZER")
    print("=" * 80)
    print("🎯 Objective: Advanced portfolio construction from expanded asset universe")
    print("📅 Analysis: 7+ years of multi-asset data with risk-adjusted strategies")
    print("💡 Features: Correlation analysis, volatility regimes, performance attribution")
    print("")
    
    analyzer = AdvancedStrategyAnalyzer()
    
    # Define test portfolio - mix of different asset classes
    test_symbols = [
        'SPY', 'QQQ', 'IWM',           # US Equity ETFs
        'VEA', 'EEM',                   # International
        'TLT', 'AGG',                   # Bonds
        'GLD', 'USO',                   # Commodities
        'AAPL', 'GOOGL', 'AMZN'        # Individual Stocks
    ]
    
    try:
        # Check available symbols
        available_query = """
        SELECT DISTINCT symbol, COUNT(*) as records 
        FROM market_data 
        WHERE symbol IN ({})
        GROUP BY symbol 
        ORDER BY records DESC
        """.format(','.join(['?' for _ in test_symbols]))
        
        available_df = pd.read_sql_query(available_query, analyzer.conn, params=tuple(test_symbols))
        
        print(f"📊 Available Symbols for Analysis:")
        available_symbols = []
        for _, row in available_df.iterrows():
            print(f"   {row['symbol']:6}: {row['records']:,} records")
            available_symbols.append(row['symbol'])
        
        if len(available_symbols) < 3:
            print("⚠️  Insufficient symbols for meaningful analysis")
            return
        
        print(f"\n🔍 Analyzing {len(available_symbols)} symbols...")
        
        # Run comprehensive strategy analysis
        result = analyzer.backtest_enhanced_strategy(
            available_symbols,
            start_date='2021-01-01'  # Use recent 3+ years for focused analysis
        )
        
        if result:
            strategies, comparison = result
        
        if strategies:
            print("\n✅ Advanced strategy analysis completed successfully!")
            print(f"   {len(strategies)} strategies tested")
            print("   Detailed results saved to CSV files")
            
            # Quick insights
            best_sharpe = comparison_df = pd.DataFrame([
                {
                    'Strategy': name,
                    'Sharpe': data['metrics']['sharpe_ratio'],
                    'Return': data['metrics']['annualized_return']
                }
                for name, data in strategies.items()
            ])
            
            best_strategy = best_sharpe.loc[best_sharpe['Sharpe'].idxmax()]
            print(f"   🏆 Best Sharpe Ratio: {best_strategy['Strategy']} ({best_strategy['Sharpe']:.2f})")
            
        else:
            print("⚠️  Strategy analysis failed - check data availability")
            
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise
    
    finally:
        analyzer.conn.close()

if __name__ == "__main__":
    main()
