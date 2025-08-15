# Asset Screening Tool for RSI + Mean Reversion Strategy
# Analyzes all available assets and ranks them for strategy suitability

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt

# Add parent directory to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from trading_strategy import RSIMeanReversionStrategy

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class AssetScreener:
    """
    Screen assets in database for RSI + Mean Reversion strategy suitability
    Ranks assets based on signal quality, volatility, and historical performance
    """
    
    def __init__(self, db_path='../Step 5: Saving Market Data/market_data.db'):
        self.db_path = db_path
        self.strategy = RSIMeanReversionStrategy()
        
        logging.info("Asset Screener initialized")
    
    def get_all_symbols(self):
        """Get all symbols available in database"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
        symbols_df = pd.read_sql_query(query, conn)
        conn.close()
        return symbols_df['symbol'].tolist()
    
    def get_symbol_data(self, symbol, days=252):
        """Get recent data for a symbol"""
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
    
    def calculate_asset_metrics(self, symbol, data):
        """Calculate comprehensive metrics for an asset"""
        if data.empty or len(data) < 50:
            return None
        
        try:
            # Basic price metrics
            returns = data['close'].pct_change().dropna()
            
            # Technical indicators
            rsi = self.strategy.calculate_rsi(data['close'])
            z_score, rolling_mean, rolling_std = self.strategy.calculate_mean_reversion_signal(data['close'])
            
            # Signal generation
            buy_signals = (rsi < 30) & (z_score < -2.0)
            sell_signals = (rsi > 70) & (z_score > 2.0)
            
            # Calculate metrics
            metrics = {
                'symbol': symbol,
                'records': len(data),
                
                # Volatility metrics
                'daily_vol': returns.std() * np.sqrt(252),  # Annualized
                'avg_volume': data['volume'].mean(),
                'price_level': data['close'].iloc[-1],
                
                # Signal metrics
                'buy_signals': buy_signals.sum(),
                'sell_signals': sell_signals.sum(),
                'total_signals': buy_signals.sum() + sell_signals.sum(),
                'signal_frequency': (buy_signals.sum() + sell_signals.sum()) / len(data) * 252,  # Annualized
                
                # RSI characteristics
                'avg_rsi': rsi.mean(),
                'rsi_std': rsi.std(),
                'rsi_oversold_pct': (rsi < 30).mean(),
                'rsi_overbought_pct': (rsi > 70).mean(),
                'rsi_extreme_pct': ((rsi < 30) | (rsi > 70)).mean(),
                
                # Mean reversion characteristics
                'avg_z_score': z_score.mean(),
                'z_score_std': z_score.std(),
                'mean_reversion_opportunities': (abs(z_score) > 2.0).sum(),
                'strong_mean_reversion': (abs(z_score) > 2.5).sum(),
                
                # Performance metrics
                'total_return': (data['close'].iloc[-1] / data['close'].iloc[0] - 1),
                'max_drawdown': self.calculate_max_drawdown(data['close']),
                'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0,
            }
            
            # Calculate suitability scores
            metrics['mean_reversion_score'] = self.calculate_mean_reversion_score(metrics)
            metrics['signal_quality_score'] = self.calculate_signal_quality_score(metrics)
            metrics['overall_score'] = (metrics['mean_reversion_score'] + metrics['signal_quality_score']) / 2
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error calculating metrics for {symbol}: {str(e)}")
            return None
    
    def calculate_max_drawdown(self, prices):
        """Calculate maximum drawdown"""
        running_max = prices.expanding().max()
        drawdown = (prices - running_max) / running_max
        return abs(drawdown.min())
    
    def calculate_mean_reversion_score(self, metrics):
        """Calculate mean reversion suitability score (0-100)"""
        score = 0
        
        # Higher volatility is better for mean reversion (but not too high)
        if 0.15 <= metrics['daily_vol'] <= 0.35:
            score += 25
        elif 0.10 <= metrics['daily_vol'] <= 0.50:
            score += 15
        
        # Good RSI distribution (not stuck in middle)
        if metrics['rsi_extreme_pct'] > 0.15:  # 15% of time in extreme zones
            score += 25
        elif metrics['rsi_extreme_pct'] > 0.10:
            score += 15
        
        # Strong mean reversion opportunities
        if metrics['mean_reversion_opportunities'] > 10:
            score += 25
        elif metrics['mean_reversion_opportunities'] > 5:
            score += 15
        
        # Manageable drawdowns
        if metrics['max_drawdown'] < 0.30:
            score += 25
        elif metrics['max_drawdown'] < 0.50:
            score += 15
        
        return min(score, 100)
    
    def calculate_signal_quality_score(self, metrics):
        """Calculate signal quality score (0-100)"""
        score = 0
        
        # Good signal frequency (not too few, not too many)
        if 10 <= metrics['signal_frequency'] <= 50:  # 10-50 signals per year
            score += 30
        elif 5 <= metrics['signal_frequency'] <= 100:
            score += 20
        
        # Balanced buy/sell signals
        if metrics['total_signals'] > 0:
            buy_ratio = metrics['buy_signals'] / metrics['total_signals']
            if 0.3 <= buy_ratio <= 0.7:  # Balanced
                score += 25
            elif 0.2 <= buy_ratio <= 0.8:
                score += 15
        
        # Sufficient data
        if metrics['records'] >= 200:
            score += 25
        elif metrics['records'] >= 100:
            score += 15
        
        # Reasonable Sharpe ratio
        if metrics['sharpe_ratio'] > 0.5:
            score += 20
        elif metrics['sharpe_ratio'] > 0:
            score += 10
        
        return min(score, 100)
    
    def screen_all_assets(self):
        """Screen all assets in database"""
        symbols = self.get_all_symbols()
        logging.info(f"Screening {len(symbols)} assets for strategy suitability")
        
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            logging.info(f"Analyzing {symbol} ({i}/{len(symbols)})")
            
            try:
                data = self.get_symbol_data(symbol)
                metrics = self.calculate_asset_metrics(symbol, data)
                
                if metrics:
                    results.append(metrics)
                    logging.info(f"✅ {symbol}: Score {metrics['overall_score']:.1f}")
                else:
                    logging.warning(f"⚠️ {symbol}: Insufficient data")
                    
            except Exception as e:
                logging.error(f"❌ {symbol}: Error - {str(e)}")
                continue
        
        return pd.DataFrame(results)
    
    def create_screening_report(self, results_df):
        """Create comprehensive screening report"""
        if results_df.empty:
            return
        
        # Sort by overall score
        results_df = results_df.sort_values('overall_score', ascending=False)
        
        print("=" * 80)
        print("ASSET SCREENING REPORT - RSI + MEAN REVERSION STRATEGY")
        print("=" * 80)
        
        print(f"\n📊 SCREENING SUMMARY")
        print(f"   Assets analyzed: {len(results_df)}")
        print(f"   Top score: {results_df['overall_score'].max():.1f}")
        print(f"   Average score: {results_df['overall_score'].mean():.1f}")
        
        # Top 10 assets
        print(f"\n🏆 TOP 10 ASSETS FOR RSI + MEAN REVERSION:")
        top_10 = results_df.head(10)
        
        for i, (_, row) in enumerate(top_10.iterrows(), 1):
            print(f"   {i:2d}. {row['symbol']:6s} - Score: {row['overall_score']:5.1f} "
                  f"(Signals: {row['total_signals']:3.0f}, Vol: {row['daily_vol']:5.1%}, "
                  f"Return: {row['total_return']:6.1%})")
        
        # Detailed analysis of top 5
        print(f"\n📈 DETAILED ANALYSIS - TOP 5 ASSETS:")
        top_5 = results_df.head(5)
        
        for _, row in top_5.iterrows():
            print(f"\n{row['symbol']} - Overall Score: {row['overall_score']:.1f}")
            print(f"   Mean Reversion Score: {row['mean_reversion_score']:.1f}")
            print(f"   Signal Quality Score: {row['signal_quality_score']:.1f}")
            print(f"   Annual Volatility: {row['daily_vol']:.1%}")
            print(f"   Signal Frequency: {row['signal_frequency']:.1f} per year")
            print(f"   RSI Extreme Time: {row['rsi_extreme_pct']:.1%}")
            print(f"   Max Drawdown: {row['max_drawdown']:.1%}")
            print(f"   Total Return: {row['total_return']:.1%}")
            print(f"   Sharpe Ratio: {row['sharpe_ratio']:.2f}")
        
        # Asset categories
        print(f"\n📋 ASSET CATEGORIES:")
        
        high_score = results_df[results_df['overall_score'] >= 70]
        medium_score = results_df[(results_df['overall_score'] >= 50) & (results_df['overall_score'] < 70)]
        low_score = results_df[results_df['overall_score'] < 50]
        
        print(f"   High Suitability (70+): {len(high_score)} assets")
        if not high_score.empty:
            print(f"      {', '.join(high_score['symbol'].tolist())}")
        
        print(f"   Medium Suitability (50-70): {len(medium_score)} assets")
        if not medium_score.empty:
            print(f"      {', '.join(medium_score['symbol'].tolist())}")
        
        print(f"   Lower Suitability (<50): {len(low_score)} assets")
        if not low_score.empty:
            print(f"      {', '.join(low_score['symbol'].tolist())}")
        
        return results_df
    
    def create_screening_visualization(self, results_df):
        """Create visualization of screening results"""
        if results_df.empty:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Asset Screening Results - RSI + Mean Reversion Strategy', fontsize=16)
        
        # 1. Score distribution
        ax1 = axes[0, 0]
        ax1.hist(results_df['overall_score'], bins=10, alpha=0.7, edgecolor='black')
        ax1.set_title('Overall Score Distribution')
        ax1.set_xlabel('Score')
        ax1.set_ylabel('Number of Assets')
        ax1.grid(True, alpha=0.3)
        
        # 2. Score components scatter
        ax2 = axes[0, 1]
        scatter = ax2.scatter(results_df['mean_reversion_score'], 
                            results_df['signal_quality_score'],
                            c=results_df['overall_score'], 
                            cmap='viridis', alpha=0.7)
        ax2.set_title('Score Components')
        ax2.set_xlabel('Mean Reversion Score')
        ax2.set_ylabel('Signal Quality Score')
        ax2.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax2, label='Overall Score')
        
        # 3. Signal frequency vs volatility
        ax3 = axes[1, 0]
        scatter = ax3.scatter(results_df['daily_vol'], 
                            results_df['signal_frequency'],
                            c=results_df['overall_score'], 
                            cmap='viridis', alpha=0.7)
        ax3.set_title('Volatility vs Signal Frequency')
        ax3.set_xlabel('Annual Volatility')
        ax3.set_ylabel('Signal Frequency (per year)')
        ax3.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax3, label='Overall Score')
        
        # 4. Top assets bar chart
        ax4 = axes[1, 1]
        top_assets = results_df.head(10)
        bars = ax4.barh(range(len(top_assets)), top_assets['overall_score'])
        ax4.set_yticks(range(len(top_assets)))
        ax4.set_yticklabels(top_assets['symbol'])
        ax4.set_title('Top 10 Assets by Score')
        ax4.set_xlabel('Overall Score')
        ax4.grid(True, alpha=0.3, axis='x')
        
        # Color bars by score
        for i, (bar, score) in enumerate(zip(bars, top_assets['overall_score'])):
            if score >= 70:
                bar.set_color('green')
            elif score >= 50:
                bar.set_color('orange')
            else:
                bar.set_color('red')
        
        plt.tight_layout()
        
        # Save plot
        filename = f'asset_screening_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\n📊 Screening visualization saved as: {filename}")
        
        plt.show()

def main():
    """Main screening function"""
    screener = AssetScreener()
    
    print("🔍 Asset Screening for RSI + Mean Reversion Strategy")
    print("=" * 60)
    
    # Run screening
    results = screener.screen_all_assets()
    
    if not results.empty:
        # Create report
        final_results = screener.create_screening_report(results)
        
        # Create visualization
        screener.create_screening_visualization(results)
        
        # Save results
        filename = f'screening_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        results.to_csv(filename, index=False)
        print(f"\n💾 Detailed results saved as: {filename}")
        
    else:
        print("❌ No screening results generated")

if __name__ == "__main__":
    main()
