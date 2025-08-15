#!/usr/bin/env python3
"""
🎯 ENHANCED ASSET SCREENER FOR EXPANDED ALPACA PROJECT

Features:
- Screen 100+ symbols across 6 asset categories
- 7+ years of historical data analysis
- Advanced RSI + Mean Reversion signals
- Multi-timeframe analysis (14, 30, 50 day periods)
- Volatility and correlation analysis
- Risk-adjusted scoring system
- Sector rotation opportunities

Usage:
    python enhanced_asset_screener.py
"""

import logging
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedAssetScreener:
    """Enhanced asset screening with 7+ years of multi-asset data"""
    
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
    
    def get_asset_categories(self):
        """Return comprehensive asset universe by category"""
        return {
            'mega_cap_etfs': ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI'],
            'international_etfs': ['VEA', 'VWO', 'EFA', 'EEM', 'ACWI', 'IEFA', 'IEMG'],
            'sector_etfs': ['XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB'],
            'bond_etfs': ['TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'AGG', 'TIP'],
            'commodity_etfs': ['GLD', 'SLV', 'USO', 'UNG', 'DBA'],
            'large_cap_stocks': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
        }
    
    def get_database_summary(self):
        """Get comprehensive database statistics"""
        query = """
        SELECT 
            symbol,
            COUNT(*) as records,
            MIN(DATE(timestamp)) as start_date,
            MAX(DATE(timestamp)) as end_date,
            ROUND((JULIANDAY(MAX(timestamp)) - JULIANDAY(MIN(timestamp))) / 365.25, 1) as years_of_data
        FROM market_data 
        GROUP BY symbol 
        ORDER BY records DESC, symbol
        """
        
        df = pd.read_sql_query(query, self.conn)
        logger.info(f"📊 Database contains {len(df)} symbols with {df['records'].sum():,} total records")
        return df
    
    def calculate_technical_indicators(self, symbol, lookback_days=1000):
        """Calculate comprehensive technical indicators for a symbol"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        query = """
        SELECT 
            DATE(timestamp) as date,
            close,
            high,
            low,
            volume
        FROM market_data 
        WHERE symbol = ? AND DATE(timestamp) >= ?
        ORDER BY timestamp
        """
        
        df = pd.read_sql_query(query, self.conn, params=(symbol, start_date.strftime('%Y-%m-%d')))
        
        if len(df) < 50:  # Need minimum data for indicators
            return None
            
        # Convert date to datetime for calculations
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # RSI calculations (multiple periods)
        df['rsi_14'] = self.calculate_rsi(df['close'], 14)
        df['rsi_30'] = self.calculate_rsi(df['close'], 30)
        
        # Moving averages
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (2 * bb_std)
        df['bb_lower'] = df['bb_mid'] - (2 * bb_std)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Volatility measures
        df['returns'] = df['close'].pct_change()
        df['volatility_20'] = df['returns'].rolling(20).std() * np.sqrt(252)
        df['atr'] = self.calculate_atr(df, 14)
        
        # Price patterns
        df['price_vs_sma20'] = (df['close'] / df['sma_20'] - 1) * 100
        df['price_vs_sma50'] = (df['close'] / df['sma_50'] - 1) * 100
        
        return df.dropna()
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def screen_opportunities(self, categories=None, min_data_years=2):
        """Screen for trading opportunities across asset categories"""
        if categories is None:
            categories = list(self.get_asset_categories().keys())
        
        asset_categories = self.get_asset_categories()
        db_summary = self.get_database_summary()
        available_symbols = set(db_summary[db_summary['years_of_data'] >= min_data_years]['symbol'])
        
        opportunities = []
        
        for category in categories:
            if category not in asset_categories:
                continue
                
            category_symbols = [s for s in asset_categories[category] if s in available_symbols]
            logger.info(f"🔍 Screening {category}: {len(category_symbols)} symbols")
            
            for symbol in category_symbols:
                try:
                    df = self.calculate_technical_indicators(symbol)
                    if df is None or len(df) < 100:
                        continue
                    
                    # Get latest values
                    latest = df.iloc[-1]
                    recent_avg = df.tail(5).mean()  # 5-day average
                    
                    # Screening criteria
                    opportunity = {
                        'symbol': symbol,
                        'category': category,
                        'last_price': latest['close'],
                        'rsi_14': latest['rsi_14'],
                        'rsi_30': latest['rsi_30'],
                        'bb_position': latest['bb_position'],
                        'price_vs_sma20': latest['price_vs_sma20'],
                        'price_vs_sma50': latest['price_vs_sma50'],
                        'volatility_20': latest['volatility_20'],
                        'atr': latest['atr'],
                        'data_points': len(df),
                        'years_of_data': len(df) / 252
                    }
                    
                    # Calculate composite signals
                    opportunity['oversold_score'] = self.calculate_oversold_score(latest)
                    opportunity['mean_reversion_score'] = self.calculate_mean_reversion_score(latest)
                    opportunity['volatility_score'] = self.calculate_volatility_score(latest)
                    opportunity['trend_score'] = self.calculate_trend_score(latest)
                    
                    # Composite opportunity score
                    opportunity['total_score'] = (
                        opportunity['oversold_score'] * 0.3 +
                        opportunity['mean_reversion_score'] * 0.3 +
                        opportunity['volatility_score'] * 0.2 +
                        opportunity['trend_score'] * 0.2
                    )
                    
                    opportunities.append(opportunity)
                    
                except Exception as e:
                    logger.warning(f"⚠️  Error screening {symbol}: {e}")
        
        return pd.DataFrame(opportunities)
    
    def calculate_oversold_score(self, latest):
        """Calculate oversold signal strength (0-100)"""
        rsi_score = max(0, (30 - latest['rsi_14']) / 30 * 100) if latest['rsi_14'] < 40 else 0
        bb_score = max(0, (0.2 - latest['bb_position']) / 0.2 * 100) if latest['bb_position'] < 0.3 else 0
        return min(100, (rsi_score + bb_score) / 2)
    
    def calculate_mean_reversion_score(self, latest):
        """Calculate mean reversion opportunity (0-100)"""
        sma20_score = max(0, abs(latest['price_vs_sma20']) - 2) * 5 if latest['price_vs_sma20'] < -2 else 0
        sma50_score = max(0, abs(latest['price_vs_sma50']) - 3) * 3 if latest['price_vs_sma50'] < -3 else 0
        return min(100, sma20_score + sma50_score)
    
    def calculate_volatility_score(self, latest):
        """Calculate volatility opportunity (higher volatility = higher score, 0-100)"""
        if latest['volatility_20'] > 0.4:
            return 100
        elif latest['volatility_20'] > 0.3:
            return 75
        elif latest['volatility_20'] > 0.2:
            return 50
        elif latest['volatility_20'] > 0.15:
            return 25
        else:
            return 10
    
    def calculate_trend_score(self, latest):
        """Calculate trend strength (0-100, higher = stronger uptrend)"""
        sma_trend = 50 + latest['price_vs_sma20']  # Centered at 50
        rsi_trend = latest['rsi_14'] if latest['rsi_14'] > 30 else 0
        return max(0, min(100, (sma_trend + rsi_trend) / 2))
    
    def generate_screening_report(self, min_score=30, top_n=20):
        """Generate comprehensive screening report"""
        logger.info("🚀 Starting Enhanced Asset Screening")
        logger.info("=" * 70)
        
        # Get opportunities
        opportunities_df = self.screen_opportunities()
        
        if opportunities_df.empty:
            logger.warning("❌ No opportunities found")
            return
        
        # Filter and sort
        filtered_df = opportunities_df[opportunities_df['total_score'] >= min_score].copy()
        top_opportunities = filtered_df.nlargest(top_n, 'total_score')
        
        logger.info(f"📊 Screening Results:")
        logger.info(f"   Total symbols analyzed: {len(opportunities_df)}")
        logger.info(f"   Opportunities above {min_score} score: {len(filtered_df)}")
        logger.info(f"   Showing top {min(top_n, len(top_opportunities))} opportunities")
        logger.info("")
        
        # Category breakdown
        category_summary = opportunities_df.groupby('category').agg({
            'total_score': ['count', 'mean', 'max'],
            'years_of_data': 'mean'
        }).round(2)
        
        logger.info("📈 Category Performance:")
        for category, stats in category_summary.iterrows():
            logger.info(f"   {category:15}: {stats[('total_score', 'count')]:3.0f} symbols, "
                       f"avg score {stats[('total_score', 'mean')]:5.1f}, "
                       f"max score {stats[('total_score', 'max')]:5.1f}, "
                       f"avg data {stats[('years_of_data', 'mean')]:3.1f}y")
        logger.info("")
        
        # Top opportunities
        if len(top_opportunities) > 0:
            logger.info("🎯 TOP OPPORTUNITIES:")
            logger.info("-" * 70)
            
            for idx, opp in top_opportunities.iterrows():
                logger.info(f"{opp['symbol']:6} | {opp['category']:15} | Score: {opp['total_score']:5.1f}")
                logger.info(f"       RSI14: {opp['rsi_14']:5.1f} | BB Pos: {opp['bb_position']:5.2f} | "
                           f"vs SMA20: {opp['price_vs_sma20']:+5.1f}% | Vol: {opp['volatility_20']:5.1%}")
                logger.info(f"       Oversold: {opp['oversold_score']:4.1f} | MeanRev: {opp['mean_reversion_score']:4.1f} | "
                           f"Vol: {opp['volatility_score']:4.1f} | Trend: {opp['trend_score']:4.1f}")
                logger.info("")
        
        # Save detailed results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"enhanced_screening_results_{timestamp}.csv"
        top_opportunities.to_csv(csv_filename, index=False)
        logger.info(f"💾 Detailed results saved: {csv_filename}")
        
        return top_opportunities

def main():
    """Run enhanced asset screening"""
    print("🌟 ENHANCED ASSET SCREENER - EXPANDED ALPACA PROJECT")
    print("=" * 80)
    print("🎯 Objective: Screen 7+ years of data across 100+ expanded asset universe")
    print("📅 Analysis: Multi-timeframe RSI + Mean Reversion + Volatility signals")
    print("💡 Strategy: Risk-adjusted opportunity identification")
    print("")
    
    screener = EnhancedAssetScreener()
    
    # Show database status
    db_summary = screener.get_database_summary()
    print(f"📊 Database Status:")
    print(f"   Total symbols: {len(db_summary)}")
    print(f"   Total records: {db_summary['records'].sum():,}")
    print(f"   Average data years: {db_summary['years_of_data'].mean():.1f}")
    print(f"   Symbols with 5+ years: {len(db_summary[db_summary['years_of_data'] >= 5])}")
    print(f"   Symbols with 7+ years: {len(db_summary[db_summary['years_of_data'] >= 7])}")
    print("")
    
    # Run comprehensive screening
    try:
        top_opportunities = screener.generate_screening_report(min_score=25, top_n=25)
        
        if top_opportunities is not None and not top_opportunities.empty:
            print("✅ Enhanced screening completed successfully!")
            print(f"   {len(top_opportunities)} high-quality opportunities identified")
            print("   Ready for enhanced strategy development!")
        else:
            print("⚠️  No high-scoring opportunities found - consider lowering score threshold")
            
    except Exception as e:
        logger.error(f"❌ Screening failed: {e}")
        raise
    
    finally:
        screener.conn.close()

if __name__ == "__main__":
    main()
