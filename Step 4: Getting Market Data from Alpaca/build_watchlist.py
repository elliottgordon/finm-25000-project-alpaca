"""
Builds watchlist.txt with:
  - All active, tradable S&P 500 constituents (via Wikipedia, filtered by Alpaca)
  - The 100 highest average-volume ETFs (active, tradable on Alpaca)

Credentials:
- Uses ALPACA_KEY / ALPACA_SECRET env vars, or
- Falls back to Alpaca_API.py at repo root (git-ignored)

Usage (from Step 4 folder):
  python build_watchlist.py
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List, Set
from step4_config import get_credentials

def _load_keys() -> Tuple[Optional[str], Optional[str]]:
    return get_credentials()


def fetch_sp500_symbols() -> List[str]:
    import pandas as pd
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    dfs = pd.read_html(url)
    df = dfs[0]
    symbols = df['Symbol'].astype(str).str.strip().str.upper().tolist()
    return symbols

def is_etf(asset) -> bool:
    # Heuristic: ARCA/NYSEARCA and name contains ETF/Trust/Fund or common ETF brands
    name = (getattr(asset, "name", "") or "").lower()
    exch = (getattr(asset, "exchange", "") or "").upper()
    keywords = [
        "etf", "exchange traded fund", "etn", "trust", "fund", "ishares",
        "spdr", "vanguard", "invesco", "schwab", "wisdomtree",
        "global x", "proshares", "direxion", "vaneck", "ark", "first trust",
        "xtrackers", "graniteshares", "horizon kinetics"
    ]
    return (exch in {"ARCA", "NYSEARCA"}) and any(k in name for k in keywords)

def build_watchlist() -> List[str]:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.trading.enums import AssetClass, AssetStatus

    key, secret = _load_keys()
    if not key or not secret:
        print("Missing credentials. Set ALPACA_KEY/ALPACA_SECRET or configure Alpaca_API.py.")
        return []

    client = TradingClient(api_key=key, secret_key=secret, paper=True)
    req = GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=AssetStatus.ACTIVE)
    assets = client.get_all_assets(req)

    # S&P 500
    try:
        sp500 = set(fetch_sp500_symbols())
    except Exception as e:
        print(f"Warning: failed to fetch S&P 500 from Wikipedia: {e}")
        sp500 = set()

    valid_alpaca_symbols = {a.symbol.upper() for a in assets if getattr(a, "tradable", False)}
    sp500_alpaca = sorted(sp500.intersection(valid_alpaca_symbols))

    # ETFs: filter, then sort by volume (descending), pick top 100
    etf_assets = [
        a for a in assets
        if getattr(a, "tradable", False) and is_etf(a)
    ]
    # Sort by volume (descending), fallback to 0 if missing
    etf_assets.sort(key=lambda a: getattr(a, "volume", 0) or 0, reverse=True)
    top_etfs = [a.symbol.upper() for a in etf_assets[:100]]

    combined = sorted(set(sp500_alpaca + top_etfs))
    return combined

def main():
    symbols = build_watchlist()
    if not symbols:
        print("No symbols collected. Aborting.")
        return
    out_path = Path(__file__).with_name("watchlist.txt")
    with open(out_path, "w") as f:
        f.write("# watchlist: S&P 500 constituents + 100 highest-volume ETFs (active, tradable on Alpaca)\n")
        f.write("# one symbol per line\n")
        for s in symbols:
            f.write(f"{s}\n")
    print(f"Wrote {len(symbols)} symbols to {out_path.name}")

if __name__ == "__main__":
    main()