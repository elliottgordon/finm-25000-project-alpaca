"""
Simple scheduler for Step 4.

- Daily: run_data_saver(symbols) after market close to persist historical bars
- Intraday: get_last_quote(symbol) periodically during market hours
- Symbols from watchlist.txt or ALPACA_SYMBOLS env var

Build mode:
  SCHEDULER_MODE=build -> run one-off historical ingestion (chunked) and exit.
"""

import os
import time
import schedule
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from typing import List

from data_collection import run_data_saver
from real_time_data import get_last_quote

ET = ZoneInfo("America/New_York")
MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

QUOTE_INTERVAL_SECONDS = int(os.getenv("QUOTE_INTERVAL_SECONDS", "30"))
HISTORICAL_RUN_TIME_ET = os.getenv("HISTORICAL_RUN_TIME_ET", "16:20")
CHUNK_SIZE = int(os.getenv("SCHEDULER_CHUNK_SIZE", "200"))
MODE = os.getenv("SCHEDULER_MODE", "").lower()  # "build" to only do historical ingestion


def load_watchlist() -> List[str]:
    env_syms = os.getenv("ALPACA_SYMBOLS")
    if env_syms:
        syms = [s.strip().upper() for s in env_syms.split(",") if s.strip()]
        if syms:
            print(f"[scheduler] Using ALPACA_SYMBOLS: {len(syms)} symbols")
            return syms

    wl_path = os.path.join(os.path.dirname(__file__), "watchlist.txt")
    if os.path.exists(wl_path):
        syms = []
        with open(wl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                syms.append(line.upper())
        if syms:
            print(f"[scheduler] Loaded watchlist.txt: {len(syms)} symbols")
            return syms

    default = ["SPY", "VXX"]
    print(f"[scheduler] Using default symbols: {default}")
    return default


def is_weekday_et(now_et: datetime | None = None) -> bool:
    if now_et is None:
        now_et = datetime.now(ET)
    return now_et.weekday() <= 4  # Mon=0 .. Fri=4


def is_market_hours_et(now_et: datetime | None = None) -> bool:
    if now_et is None:
        now_et = datetime.now(ET)
    return is_weekday_et(now_et) and (MARKET_OPEN <= now_et.time() <= MARKET_CLOSE)


def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"[scheduler] Error calling {fn.__name__}: {e}")


def job_historical(symbols: List[str]):
    if not is_weekday_et():
        print("[scheduler] Skipping historical job (weekend).")
        return
    total = len(symbols)
    print(f"[scheduler] Historical ingestion for {total} symbols (chunk={CHUNK_SIZE})")
    for i in range(0, total, CHUNK_SIZE):
        chunk = symbols[i:i + CHUNK_SIZE]
        print(f"[scheduler] Processing {i + 1}-{i + len(chunk)} of {total}...")
        safe_call(run_data_saver, chunk)
        time.sleep(1)  # small pause between chunks
    print("[scheduler] Historical saver done.")


def job_last_quotes(symbols: List[str]):
    if not is_market_hours_et():
        return
    for sym in symbols:
        safe_call(get_last_quote, sym)
        time.sleep(0.2)  # gentle pacing


def main():
    symbols = load_watchlist()

    if MODE == "build":
        print("[scheduler] MODE=build -> one-off historical build then exit.")
        job_historical(symbols)
        print("[scheduler] Build complete.")
        return

    # Intraday quotes (skip if the list is huge)
    if len(symbols) <= 500:
        schedule.every(QUOTE_INTERVAL_SECONDS).seconds.do(job_last_quotes, symbols)
    else:
        print(f"[scheduler] Large watchlist ({len(symbols)}). Skipping intraday quotes.")

    # Historical saver after close each weekday
    schedule.every().monday.at(HISTORICAL_RUN_TIME_ET).do(job_historical, symbols)
    schedule.every().tuesday.at(HISTORICAL_RUN_TIME_ET).do(job_historical, symbols)
    schedule.every().wednesday.at(HISTORICAL_RUN_TIME_ET).do(job_historical, symbols)
    schedule.every().thursday.at(HISTORICAL_RUN_TIME_ET).do(job_historical, symbols)
    schedule.every().friday.at(HISTORICAL_RUN_TIME_ET).do(job_historical, symbols)

    print("[scheduler] Started. Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[scheduler] Stopped.")


if __name__ == "__main__":
    main()