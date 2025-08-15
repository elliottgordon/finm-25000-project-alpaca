"""
Enhanced Multi-Asset Data Collector with 7+ Years Historical Data
Maximizes data collection using Alpaca's free tier capabilities
"""

import os
import sys

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from Alpaca_API import ALPACA_KEY, ALPACA_SECRET
from asset_universe import get_priority_universe, get_all_symbols, get_etf_universe

# Import alpaca API
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.enums import Adjustment
from alpaca.data.timeframe import TimeFrame

import sqlalchemy
import pandas as pd
import pytz
from datetime import datetime, timedelta, date
import logging
import time
import json

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_data_collector.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ComprehensiveDataCollector:
    def __init__(self, max_years_history=8):
        """Initialize with maximum historical data collection"""
        self.client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
        self.max_years_history = max_years_history
        self.eastern = pytz.timezone('US/Eastern')
        
        # Calculate start date for maximum historical data
        # Going back 8 years to ensure we get 7+ years of data
        self.start_date = self.eastern.localize(
            datetime(datetime.now().year - max_years_history, 1, 1)
        )
        self.end_date = self.eastern.localize(
            datetime.now() - timedelta(days=1)
        )
        
        # Rate limiting parameters (Alpaca Basic: 200 API calls/min)
        self.batch_size = 2  # Small batches to be conservative
        self.delay_between_requests = 1.0  # 1 second delay
        self.delay_between_batches = 3.0  # 3 second delay
        
        # Database setup
        db_path = os.path.join(os.path.dirname(__file__), '..', 'Step 5: Saving Market Data', 'market_data.db')
        self.engine = sqlalchemy.create_engine(f'sqlite:///{db_path}')
        
        logger.info(f"📅 Historical data range: {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"📊 Years of data: {self.max_years_history}")
        
    def get_expanded_asset_universe(self):
        """Get significantly expanded asset universe with new additions"""
        
        # Enhanced Index ETFs (more international and specialized)
        enhanced_index_etfs = [
            'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VEA', 'VWO', 'EFA', 'EEM',
            'ACWI',  # All World ex-US
            'IEFA',  # Core MSCI EAFE
            'IEMG',  # Core MSCI Emerging Markets
            'VGK',   # FTSE Europe
            'VPL',   # FTSE Pacific
            'INDA',  # MSCI India
            'FXI',   # Large Cap China
            'VNQ',   # REITs
            'VTEB',  # Tax-Exempt Bond
            'VB',    # Small Cap
            'VV',    # Large Cap
            'VXUS'   # Total International Stock
        ]
        
        # Enhanced Sector ETFs (include more granular sectors)
        enhanced_sector_etfs = [
            'XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC',
            'VGT',   # Information Technology
            'VFH',   # Financials
            'VHT',   # Health Care
            'VDE',   # Energy
            'VIS',   # Industrials
            'VCR',   # Consumer Discretionary
            'VDC',   # Consumer Staples
            'VPU',   # Utilities
            'VAW',   # Materials
            'VOX',   # Communication Services
            'IYW',   # Technology
            'IYF',   # Financial Services
            'IYH',   # Healthcare
            'IYE',   # Energy
            'IYJ',   # Industrials
            'IYC',   # Consumer Services
            'IYK',   # Consumer Goods
            'IDU',   # Utilities
            'IYM',   # Materials
        ]
        
        # Enhanced Bond/Fixed Income ETFs
        enhanced_bond_etfs = [
            'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'AGG', 'TIP', 'JNK',
            'BND',   # Total Bond Market
            'VGIT',  # Intermediate Government
            'VGLT',  # Long Government
            'VGSH',  # Short Government
            'VTC',   # Total Corporate
            'VCIT',  # Intermediate Corporate
            'VCLT',  # Long Corporate
            'VCSH',  # Short Corporate
            'BNDX',  # Total International Bond
            'VWOB',  # Emerging Markets Government Bond
            'EMB',   # Emerging Markets Bond
            'SCHZ',  # US Tips ETF
            'VTIP',  # Short-Term Inflation-Protected Securities
            'MUB',   # National Municipal Bond
        ]
        
        # Enhanced Commodity/Currency ETFs
        enhanced_commodity_etfs = [
            'GLD', 'SLV', 'USO', 'UNG', 'DBA', 'PDBC', 'GLTR', 'UUP', 'FXE',
            'IAU',   # Gold Trust
            'SGOL',  # Gold Shares
            'PPLT',  # Platinum
            'PALL',  # Palladium
            'CORN',  # Corn
            'WEAT',  # Wheat
            'SOYB',  # Soybeans
            'CANE',  # Sugar
            'NIB',   # Cocoa
            'JO',    # Coffee
            'UCO',   # 2x Oil
            'SCO',   # -2x Oil
            'BOIL',  # 2x Natural Gas
            'KOLD',  # -2x Natural Gas
            'FXB',   # British Pound
            'FXC',   # Canadian Dollar
            'FXY',   # Japanese Yen
            'CYB',   # Chinese Yuan
        ]
        
        # Top performing large cap stocks (more comprehensive)
        enhanced_large_cap_stocks = [
            # Mega-cap Technology
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'ADBE',
            'CRM', 'ORCL', 'CSCO', 'INTC', 'AMD', 'PYPL', 'UBER', 'SNOW', 'SHOP', 'DOCU',
            'ZM', 'ROKU', 'SQ', 'TWTR', 'SPOT', 'PINS', 'SNAP', 'LYFT', 'ABNB', 'COIN',
            
            # Healthcare & Biotech
            'UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY', 'MRK', 'LLY',
            'GILD', 'AMGN', 'VRTX', 'REGN', 'BIIB', 'ILMN', 'MRNA', 'JNJ', 'CVS', 'CI',
            
            # Financial Services
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'SCHW', 'USB',
            'PNC', 'TFC', 'COF', 'AFL', 'AIG', 'PRU', 'MET', 'ALL', 'TRV', 'CB',
            
            # Consumer & Retail
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'MCD', 'NKE', 'SBUX', 'TGT', 'COST',
            'LOW', 'DIS', 'CMCSA', 'VZ', 'T', 'PM', 'MO', 'CL', 'KMB', 'GIS',
            
            # Energy & Industrials
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'PSX', 'MPC', 'VLO', 'HES',
            'BA', 'CAT', 'DE', 'GE', 'LMT', 'RTX', 'HON', 'UPS', 'FDX', 'WM',
            
            # High-growth stocks
            'ARKK', 'ARKG', 'ARKW', 'ARKF', 'ARKQ',  # ARK Innovation ETFs
            'ICLN', 'QCLN', 'PBW', 'FAN', 'LIT',     # Clean Energy
            'HACK', 'CIBR', 'BUG', 'IHAK', 'SNSR',  # Cybersecurity
            'ROBO', 'BOTZ', 'IRBO', 'UBOT', 'THNQ', # Robotics/AI
        ]
        
        # Volatility and alternative strategies
        volatility_alternative = [
            'VXX', 'VIXY', 'UVXY', 'SVXY', 'VXZ', 'VIXM', 'TVIX', 'XIV',
            'SPLV', 'USMV', 'EEMV', 'EFAV',  # Low volatility
            'MTUM', 'VMOT', 'PDP', 'FDMO',   # Momentum
            'QUAL', 'DGRW', 'DGRO', 'VIG',   # Quality/Dividend Growth
        ]
        
        # Combine all categories
        comprehensive_universe = {
            'tier_1_index_etfs': enhanced_index_etfs,
            'tier_2_sector_etfs': enhanced_sector_etfs,  
            'tier_3_bond_etfs': enhanced_bond_etfs,
            'tier_4_commodity_etfs': enhanced_commodity_etfs,
            'tier_5_large_cap_stocks': enhanced_large_cap_stocks,
            'tier_6_volatility_alternative': volatility_alternative,
        }
        
        # Log the expansion
        total_symbols = sum(len(symbols) for symbols in comprehensive_universe.values())
        logger.info(f"🎯 Comprehensive Universe: {total_symbols} total symbols")
        for tier, symbols in comprehensive_universe.items():
            logger.info(f"   {tier}: {len(symbols)} symbols")
            
        return comprehensive_universe
    
    def get_historical_data_batch(self, symbols, start_date, end_date):
        """Get historical data for a batch of symbols with error handling"""
        batch_data = []
        
        for symbol in symbols:
            try:
                logger.info(f"📊 Requesting data for {symbol}")
                
                request_params = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date,
                    adjustment=Adjustment.ALL
                )
                
                bars = self.client.get_stock_bars(request_params).df.reset_index()
                
                if not bars.empty:
                    # Add data quality metrics
                    data_start = bars['timestamp'].min().strftime('%Y-%m-%d')
                    data_end = bars['timestamp'].max().strftime('%Y-%m-%d')
                    years_of_data = (bars['timestamp'].max() - bars['timestamp'].min()).days / 365.25
                    
                    batch_data.append(bars)
                    logger.info(f"✅ {symbol}: {len(bars):,} records ({data_start} to {data_end}, {years_of_data:.1f} years)")
                else:
                    logger.warning(f"⚠️ {symbol}: No data available")
                
                # Respect rate limits
                time.sleep(self.delay_between_requests)
                
            except Exception as e:
                logger.error(f"❌ {symbol}: {str(e)}")
                continue
        
        if batch_data:
            combined = pd.concat(batch_data, ignore_index=True)
            return combined
        else:
            return pd.DataFrame()
    
    def get_database_summary(self):
        """Get comprehensive database summary"""
        try:
            # Total records
            total_query = "SELECT COUNT(*) as total_records FROM market_data"
            total_result = pd.read_sql(total_query, self.engine)
            total_records = total_result['total_records'].iloc[0]
            
            # Unique symbols
            symbols_query = "SELECT DISTINCT symbol FROM market_data"
            symbols_result = pd.read_sql(symbols_query, self.engine)
            unique_symbols = len(symbols_result)
            
            # Date range
            date_range_query = """
                SELECT 
                    MIN(timestamp) as earliest_date,
                    MAX(timestamp) as latest_date
                FROM market_data
            """
            date_result = pd.read_sql(date_range_query, self.engine)
            
            # Symbol-level summary
            symbol_summary_query = """
                SELECT 
                    symbol,
                    COUNT(*) as record_count,
                    MIN(timestamp) as start_date,
                    MAX(timestamp) as end_date,
                    AVG(volume) as avg_volume
                FROM market_data 
                GROUP BY symbol 
                ORDER BY record_count DESC
            """
            symbol_summary = pd.read_sql(symbol_summary_query, self.engine)
            
            return {
                'total_records': total_records,
                'unique_symbols': unique_symbols,
                'date_range': date_result.iloc[0].to_dict(),
                'symbol_summary': symbol_summary
            }
        except Exception as e:
            logger.error(f"❌ Database summary error: {str(e)}")
            return None
    
    def save_data_to_database(self, data_df):
        """Save data to database with deduplication"""
        if data_df.empty:
            logger.warning("⚠️ No data to save")
            return 0
        
        try:
            # Remove duplicates within the new data
            data_df = data_df.drop_duplicates(subset=['symbol', 'timestamp'])
            
            # Save to database (append mode)
            data_df.to_sql('market_data', self.engine, if_exists='append', index=False)
            
            logger.info(f"💾 Saved {len(data_df):,} records to database")
            return len(data_df)
            
        except Exception as e:
            logger.error(f"❌ Database save error: {str(e)}")
            return 0
    
    def run_comprehensive_collection(self, tiers_to_collect=None, max_symbols_per_tier=None):
        """Run comprehensive data collection across all tiers"""
        
        logger.info("🚀 Starting Comprehensive Multi-Asset Data Collection")
        logger.info("=" * 80)
        
        # Get expanded universe
        universe = self.get_expanded_asset_universe()
        
        # Default to all tiers if not specified
        if tiers_to_collect is None:
            tiers_to_collect = list(universe.keys())
        
        collection_summary = {
            'tiers_processed': [],
            'total_symbols_attempted': 0,
            'total_records_collected': 0,
            'successful_symbols': [],
            'failed_symbols': [],
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        # Process each tier
        for tier_name in tiers_to_collect:
            if tier_name not in universe:
                logger.warning(f"⚠️ Unknown tier: {tier_name}")
                continue
                
            symbols = universe[tier_name]
            
            # Limit symbols per tier if specified
            if max_symbols_per_tier:
                symbols = symbols[:max_symbols_per_tier]
            
            logger.info(f"\n🎯 Processing {tier_name}: {len(symbols)} symbols")
            logger.info(f"   Symbols: {symbols[:10]}{'...' if len(symbols) > 10 else ''}")
            
            tier_records = 0
            tier_successful = []
            tier_failed = []
            
            # Process in batches
            for i in range(0, len(symbols), self.batch_size):
                batch = symbols[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"📦 Batch {batch_num}/{total_batches}: {batch}")
                
                # Get data for batch
                batch_data = self.get_historical_data_batch(
                    batch, self.start_date, self.end_date
                )
                
                # Save to database
                if not batch_data.empty:
                    records_saved = self.save_data_to_database(batch_data)
                    tier_records += records_saved
                    
                    # Track successful symbols
                    successful_in_batch = batch_data['symbol'].unique().tolist()
                    tier_successful.extend(successful_in_batch)
                    
                    # Track failed symbols
                    failed_in_batch = [s for s in batch if s not in successful_in_batch]
                    tier_failed.extend(failed_in_batch)
                else:
                    tier_failed.extend(batch)
                
                # Delay between batches
                if i + self.batch_size < len(symbols):
                    logger.info(f"⏳ Waiting {self.delay_between_batches}s before next batch...")
                    time.sleep(self.delay_between_batches)
            
            # Tier summary
            logger.info(f"✅ {tier_name} completed:")
            logger.info(f"   Records collected: {tier_records:,}")
            logger.info(f"   Successful symbols: {len(tier_successful)}")
            logger.info(f"   Failed symbols: {len(tier_failed)}")
            
            collection_summary['tiers_processed'].append({
                'tier': tier_name,
                'symbols_attempted': len(symbols),
                'records_collected': tier_records,
                'successful_symbols': tier_successful,
                'failed_symbols': tier_failed
            })
            
            collection_summary['total_symbols_attempted'] += len(symbols)
            collection_summary['total_records_collected'] += tier_records
            collection_summary['successful_symbols'].extend(tier_successful)
            collection_summary['failed_symbols'].extend(tier_failed)
        
        # Final processing time
        end_time = datetime.now()
        collection_summary['processing_time'] = (end_time - start_time).total_seconds()
        
        # Get final database summary
        db_summary = self.get_database_summary()
        
        # Final report
        logger.info("\n" + "🎉 COMPREHENSIVE COLLECTION COMPLETE" + "=" * 50)
        logger.info(f"⏱️  Processing time: {collection_summary['processing_time']:.1f} seconds")
        logger.info(f"🎯 Symbols attempted: {collection_summary['total_symbols_attempted']}")
        logger.info(f"✅ Successful symbols: {len(collection_summary['successful_symbols'])}")
        logger.info(f"❌ Failed symbols: {len(collection_summary['failed_symbols'])}")
        logger.info(f"📊 Records collected this session: {collection_summary['total_records_collected']:,}")
        
        if db_summary:
            logger.info(f"💾 Total database records: {db_summary['total_records']:,}")
            logger.info(f"🎵 Total unique symbols in DB: {db_summary['unique_symbols']}")
            
            if db_summary['date_range']['earliest_date'] and db_summary['date_range']['latest_date']:
                earliest = pd.to_datetime(db_summary['date_range']['earliest_date']).date()
                latest = pd.to_datetime(db_summary['date_range']['latest_date']).date()
                years_span = (latest - earliest).days / 365.25
                logger.info(f"📅 Database date range: {earliest} to {latest} ({years_span:.1f} years)")
        
        return collection_summary, db_summary

def main():
    """Main execution function"""
    collector = ComprehensiveDataCollector(max_years_history=8)
    
    print("🌟 COMPREHENSIVE MULTI-ASSET DATA COLLECTION")
    print("=" * 80)
    print(f"📅 Target date range: 8 years of historical data")
    print(f"🎯 Objective: Maximize asset universe for enhanced strategy development")
    print(f"💡 Using Alpaca's free tier: 7+ years historical data, 200 API calls/min")
    
    # Show available tiers
    universe = collector.get_expanded_asset_universe()
    print(f"\n📊 Available Asset Tiers ({sum(len(s) for s in universe.values())} total symbols):")
    for tier, symbols in universe.items():
        print(f"   {tier.replace('_', ' ').title()}: {len(symbols)} symbols")
    
    # Configuration options
    print(f"\n⚙️ Collection Strategy Options:")
    print(f"   1. Conservative: ETFs only (Tiers 1-3)")
    print(f"   2. Moderate: ETFs + Top Large Caps (Tiers 1-4, limited)")
    print(f"   3. Comprehensive: All tiers (may take several hours)")
    print(f"   4. Custom: Specify tiers and limits")
    
    # For now, let's start with a moderate approach
    selected_tiers = ['tier_1_index_etfs', 'tier_2_sector_etfs', 'tier_3_bond_etfs']
    max_per_tier = 25  # Limit to first 25 symbols per tier to start
    
    print(f"\n🎯 Selected Strategy: Moderate")
    print(f"   Tiers: {selected_tiers}")
    print(f"   Max symbols per tier: {max_per_tier}")
    
    # Run collection
    collection_summary, db_summary = collector.run_comprehensive_collection(
        tiers_to_collect=selected_tiers,
        max_symbols_per_tier=max_per_tier
    )
    
    # Save collection report
    report = {
        'collection_time': datetime.now().isoformat(),
        'collection_summary': collection_summary,
        'database_summary': db_summary
    }
    
    with open('comprehensive_collection_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: comprehensive_collection_report.json")

if __name__ == "__main__":
    main()
