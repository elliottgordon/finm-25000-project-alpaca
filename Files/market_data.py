
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.historical.corporate_actions import CorporateActionsClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.stream import TradingStream
from alpaca.data.live.stock import StockDataStream

from alpaca.data.requests import (
    CorporateActionsRequest,
    StockBarsRequest,
    StockQuotesRequest,
    StockTradesRequest,
)
from alpaca.trading.requests import (
    ClosePositionRequest,
    GetAssetsRequest,
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLimitOrderRequest,
    StopLossRequest,
    StopOrderRequest,
    TakeProfitRequest,
    TrailingStopOrderRequest,
)
from alpaca.trading.enums import (
    AssetExchange,
    AssetStatus,
    OrderClass,
    OrderSide,
    OrderType,
    QueryOrderStatus,
    TimeInForce,
)

import os
import pickle
import alpaca_trade_api as tradeapi
import pandas as pd
from alpaca_api import ALPACA_KEY, ALPACA_SECRET
import os
from alpaca.data import CryptoHistoricalDataClient, StockHistoricalDataClient, OptionHistoricalDataClient, TimeFrame
from datetime import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

BASE_URL = "https://paper-api.alpaca.markets"

# no keys required.
crypto_client = CryptoHistoricalDataClient()

# keys required
stock_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
option_client = OptionHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

# get historical bars by symbol
# ref. https://docs.alpaca.markets/reference/stockbars-1

now = datetime.now(ZoneInfo("America/New_York"))
req = StockBarsRequest(
    symbol_or_symbols = ["SPY", "AAPL", "GOOGL"],               # specify symbol or symbols
    timeframe=TimeFrame(amount = 1, unit = TimeFrameUnit.Hour), # specify timeframe
    start = now - timedelta(days = 5),                          # specify start datetime, default=the beginning of the current day.
    # end_date=None,                                        # specify end datetime, default=now
    limit = 2,                                               # specify limit
)
stock_client.get_stock_bars(req).df


