import os

PYTHON_DIR = os.path.dirname(os.path.realpath(__file__))
LOGS_DIR = os.path.join(PYTHON_DIR, "logs")

EXCHANGES = {
    "bitfinex": {
        "fees": (0.002, 1),
        "pairs": ["eth/usd", "eth/btc", "btc/usd", "dai/usd", "dai/eth", "dai/btc"],
    },
    "kraken": {
        "fees": (0.0026, 1),
        "pairs": ["eth/usd", "eth/btc", "eth/dai", "btc/usd", "btc/dai", "dai/usd"],
    },
    "binance": {"fees": (0.001, 1), "pairs": ["eth/btc"]},
    "bittrex": {
        "fees": (0.002, 1),
        "pairs": ["eth/usd", "eth/btc", "eth/dai", "btc/usd", "btc/dai", "dai/usd"],
    },
    "loopring": {"fees": (0, 1), "pairs": ["eth/dai"],},
}

SLEEP_TIME = 10
