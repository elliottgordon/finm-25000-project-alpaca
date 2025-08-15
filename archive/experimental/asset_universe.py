# Asset Universe Configuration for RSI + Mean Reversion Strategy
# Comprehensive list of assets suitable for mean reversion trading

# ETF Universe - Primary targets (high liquidity, stable microstructure)
INDEX_ETFS = [
    'SPY',   # S&P 500
    'QQQ',   # NASDAQ 100
    'IWM',   # Russell 2000
    'DIA',   # Dow Jones
    'VTI',   # Total Stock Market
    'VEA',   # Developed Markets ex-US
    'VWO',   # Emerging Markets
    'EFA',   # MSCI EAFE
    'EEM',   # Emerging Markets MSCI
]

SECTOR_ETFS = [
    'XLK',   # Technology
    'XLF',   # Financials
    'XLV',   # Healthcare
    'XLE',   # Energy
    'XLI',   # Industrials
    'XLY',   # Consumer Discretionary
    'XLP',   # Consumer Staples
    'XLU',   # Utilities
    'XLB',   # Materials
    'XLRE',  # Real Estate
    'XLC',   # Communication Services
]

BOND_ETFS = [
    'TLT',   # 20+ Year Treasury
    'IEF',   # 7-10 Year Treasury
    'SHY',   # 1-3 Year Treasury
    'LQD',   # Investment Grade Corporate
    'HYG',   # High Yield Corporate
    'AGG',   # Total Bond Market
    'TIP',   # Treasury Inflation Protected
    'JNK',   # High Yield Bonds
]

COMMODITY_ETFS = [
    'GLD',   # Gold
    'SLV',   # Silver
    'USO',   # Oil
    'UNG',   # Natural Gas
    'DBA',   # Agriculture
    'PDBC',  # Commodities
    'GLTR',  # Precious Metals
    'UUP',   # US Dollar
    'FXE',   # Euro Currency
]

# Volatility ETPs (Higher risk - shorter holding periods recommended)
VOLATILITY_ETPS = [
    'VXX',   # VIX Short-term futures
    'VIXY',  # VIX Short-term futures
    'UVXY',  # 2x VIX Short-term futures (high risk)
    'SVXY',  # Short VIX Short-term futures (high risk)
]

# Large Cap Stocks - High liquidity single names
LARGE_CAP_STOCKS = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'AMZN', 'NVDA', 'TSLA', 'NFLX', 'ADBE',
    'CRM', 'ORCL', 'CSCO', 'INTC', 'AMD', 'PYPL', 'UBER', 'SNOW', 'SHOP',
    
    # Healthcare
    'UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY', 'MRK', 'LLY',
    
    # Financials
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'SCHW', 'USB',
    
    # Consumer & Retail
    'WMT', 'HD', 'PG', 'KO', 'PEP', 'MCD', 'NKE', 'SBUX', 'TGT', 'COST',
    
    # Energy & Industrial
    'XOM', 'CVX', 'COP', 'EOG', 'BA', 'CAT', 'DE', 'GE', 'LMT', 'RTX',
]

# Crypto (if supported by your Alpaca plan)
CRYPTO_SYMBOLS = [
    'BTCUSD',  # Bitcoin
    'ETHUSD',  # Ethereum
    'LTCUSD',  # Litecoin
    'BCHUSD',  # Bitcoin Cash
]

def get_priority_universe():
    """Get prioritized asset list starting with most suitable for mean reversion"""
    return {
        'tier_1_etfs': INDEX_ETFS + SECTOR_ETFS,  # Highest priority
        'tier_2_bonds': BOND_ETFS,                # Good for mean reversion
        'tier_3_commodities': COMMODITY_ETFS,     # Moderate priority
        'tier_4_stocks': LARGE_CAP_STOCKS[:20],   # Top 20 large caps
        'tier_5_volatility': VOLATILITY_ETPS,     # High risk, use carefully
    }

def get_all_symbols():
    """Get complete list of all symbols"""
    all_symbols = (INDEX_ETFS + SECTOR_ETFS + BOND_ETFS + 
                   COMMODITY_ETFS + VOLATILITY_ETPS + LARGE_CAP_STOCKS)
    return sorted(list(set(all_symbols)))

def get_etf_universe():
    """Get just ETF symbols (recommended starting point)"""
    etf_symbols = INDEX_ETFS + SECTOR_ETFS + BOND_ETFS + COMMODITY_ETFS
    return sorted(list(set(etf_symbols)))

def get_conservative_universe():
    """Get conservative universe for initial testing"""
    return sorted(INDEX_ETFS + SECTOR_ETFS[:6])  # Top 6 sector ETFs

# Asset metadata for strategy optimization
ASSET_CHARACTERISTICS = {
    # Mean reversion suitability: high/medium/low
    # Volatility: high/medium/low  
    # News sensitivity: high/medium/low
    'SPY': {'mean_reversion': 'high', 'volatility': 'medium', 'news_sensitivity': 'low'},
    'QQQ': {'mean_reversion': 'medium', 'volatility': 'high', 'news_sensitivity': 'medium'},
    'IWM': {'mean_reversion': 'high', 'volatility': 'high', 'news_sensitivity': 'low'},
    'VXX': {'mean_reversion': 'low', 'volatility': 'high', 'news_sensitivity': 'high'},
    'TLT': {'mean_reversion': 'high', 'volatility': 'medium', 'news_sensitivity': 'medium'},
    'XLU': {'mean_reversion': 'high', 'volatility': 'low', 'news_sensitivity': 'low'},
    'XLF': {'mean_reversion': 'medium', 'volatility': 'high', 'news_sensitivity': 'high'},
    'GLD': {'mean_reversion': 'medium', 'volatility': 'medium', 'news_sensitivity': 'medium'},
}

if __name__ == "__main__":
    print("Asset Universe for RSI + Mean Reversion Strategy")
    print("=" * 60)
    
    priority = get_priority_universe()
    for tier, symbols in priority.items():
        print(f"\n{tier.upper().replace('_', ' ')}: ({len(symbols)} symbols)")
        print(f"  {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    
    print(f"\nTotal Universe: {len(get_all_symbols())} symbols")
    print(f"Conservative Start: {len(get_conservative_universe())} symbols")
