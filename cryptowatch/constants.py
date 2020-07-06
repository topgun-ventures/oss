import os

PYTHON_DIR = os.path.dirname(os.path.realpath(__file__))
LOGS_DIR = os.path.join(PYTHON_DIR, "logs")

CRPW_HOST = "https://api.cryptowat.ch/"
CRPW_ORDERBOOK_URL = CRPW_HOST + "markets/{}/{}/orderbook"
CRPW_TRADES_URL = CRPW_HOST + "markets/{}/{}/trades"
CRPW_MARKETS = CRPW_HOST + "markets"

EXCHANGES = {
    "bitfinex": ["daiusd"],
    "kraken": ["daiusd", "daieur", "daiusdt"],
    "coinbase-pro": ["daiusdc"],
    "hitbtc": ["usdtdai", "daiusdc"],
}

TABLES = ["ask_orderbooks", "bid_orderbooks"]

SLEEP_TIME = 1800
