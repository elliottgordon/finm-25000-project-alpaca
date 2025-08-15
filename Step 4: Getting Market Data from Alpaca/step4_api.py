"""
Simple, readable wrappers around alpaca-py for Step 4.
- Uses daily bars for stocks/ETFs.
- Keeps parameters explicit and easy to follow.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, cast
import time
import os
import sys

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.enums import Adjustment
from alpaca.data.timeframe import TimeFrame

# Allow importing step4_config.py from this folder (folder is not a Python package)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step4_config import get_credentials


def make_client() -> StockHistoricalDataClient:
    key, secret = get_credentials()
    return StockHistoricalDataClient(key, secret)


def _with_simple_backoff(callable_fn, *args, **kwargs):
    """Run callable with simple retry/backoff for HTTP 429/5xx. Keeps it basic."""
    delays = [0, 1, 2, 4]  # seconds
    last_exc = None
    for delay in delays:
        if delay:
            time.sleep(delay)
        try:
            return callable_fn(*args, **kwargs)
        except Exception as e:
            # If the exception message hints at rate limiting or server issues, retry
            msg = str(e).lower()
            if "429" in msg or "rate" in msg or "server" in msg or "timeout" in msg:
                last_exc = e
                continue
            # Otherwise, re-raise immediately
            raise
    # exhausted retries
    if last_exc:
        raise last_exc
    raise RuntimeError("Request failed after retries")


def _bars_response_to_df(resp) -> pd.DataFrame:
    """Normalize bars response to a DataFrame safely."""
    # Common path in alpaca-py: response has a .df property
    try:
        df = resp.df
        if hasattr(df, "reset_index"):
            return df.reset_index()
    except Exception:
        pass

    # Fallback: build DataFrame from resp.data
    rows = []
    data = getattr(resp, "data", {})
    for symbol, barset in (data.items() if hasattr(data, "items") else []):
        for bar in barset:
            rows.append(
                {
                    "timestamp": getattr(bar, "timestamp", None),
                    "symbol": symbol,
                    "open": getattr(bar, "open", None),
                    "high": getattr(bar, "high", None),
                    "low": getattr(bar, "low", None),
                    "close": getattr(bar, "close", None),
                    "volume": getattr(bar, "volume", None),
                    "trade_count": getattr(bar, "trade_count", None),
                    "vwap": getattr(bar, "vwap", None),
                }
            )
    return pd.DataFrame(rows)


def get_daily_bars(
    symbols: Iterable[str],
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    """Fetch daily OHLCV bars for one or more symbols.

    Returns a DataFrame with columns including: timestamp, symbol, open, high, low, close, volume
    """
    client = make_client()
    timeframe_obj = cast(TimeFrame, TimeFrame.Day)
    req = StockBarsRequest(
        symbol_or_symbols=list(symbols),
        timeframe=timeframe_obj,
        start=start,
        end=end,
        adjustment=Adjustment.ALL,
    )
    resp = _with_simple_backoff(client.get_stock_bars, req)
    return _bars_response_to_df(resp)


def get_latest_quotes(symbols: Iterable[str]):
    client = make_client()
    req = StockLatestQuoteRequest(symbol_or_symbols=list(symbols))
    return _with_simple_backoff(client.get_stock_latest_quote, req)
