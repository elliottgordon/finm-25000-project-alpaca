# Step 4: Getting Market Data from Alpaca

Clean, basic scripts to fetch daily stock/ETF data with the modern `alpaca-py` SDK.

## What’s in this folder
- `step4_config.py` — reads `ALPACA_KEY`/`ALPACA_SECRET` from env or falls back to root `Alpaca_API.py` (git-ignored)
- `step4_api.py` — simple wrappers: get daily bars, get latest quotes (with tiny retry/backoff)
- `sample_fetch.py` — minimal example to fetch 30 days of SPY/VXX and print
- `data_collection.py` — basic daily fetch that writes to `../Step 5: Saving Market Data/market_data.db`
- `real_time_data.py` — example of using a latest-quote endpoint
- `enhanced_asset_screener.py` — optional helper to pick assets for Step 4

## Step 4 sub-steps: status and pointers
1) Choose the asset to trade — DONE
- Use the default symbols in `sample_fetch.py` / `data_collection.py`, or customize.
- Optional: `enhanced_asset_screener.py` can help pick a list.

2) Explore Alpaca GitHub — DONE (by implementation)
- Code uses the modern `alpaca-py` SDK (`alpaca.data.*`).

3) Install alpaca-py — DONE
- The project venv already includes `alpaca-py`. If needed, install in your env.

4) Review API docs — DONE (reflected in code)
- Uses `StockHistoricalDataClient`, `StockBarsRequest`, `TimeFrame.Day`, `Adjustment.ALL`.

5) Understand symbols and market hours — DONE
- Daily timeframe and US/Eastern timezone handling in `data_collection.py`.
- Simple weekday check before updating.

6) Sample code for getting market data — DONE
- `sample_fetch.py` (quick preview)
- `step4_api.get_daily_bars()` (reusable helper)

7) Handle authentication and rate limits — DONE
- Auth: `step4_config.py` loads from env or root `Alpaca_API.py` (git-ignored by `.gitignore`).
- Rate-limit friendliness: small retry/backoff in `step4_api.py`.

8) Explore additional endpoints — DONE
- `real_time_data.py` demonstrates latest quotes.

## Quick start
1) Credentials (pick one):
- Set env vars `ALPACA_KEY` and `ALPACA_SECRET`, or
- Put keys in root `Alpaca_API.py` (kept out of git).

2) Run a minimal sample from this folder:
```bash
# optional: source ../alpaca_venv/bin/activate
python sample_fetch.py
```

3) Save data to the Step 5 database:
```bash
python data_collection.py
```

## Security
- `Alpaca_API.py` is ignored by git. Keep keys private; consider env vars for local/dev use.

## Optional improvements
- If you plan heavy collection, add a token-bucket rate limiter shared by scripts.
