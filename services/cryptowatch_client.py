import os

import requests
import pandas as pd
from datetime import datetime, timedelta
from services.finance import rsi

base_url = "https://api.cryptowat.ch"

headers = {"Content-Type": "application/json"}

rsi_type = {"minute": 60, "hour": 3600, "12h": 43200, "day": 86400, "week": 604800}


def get_url(url):
    return base_url + url


class CryptowatchClient:
    def _request(self, path, params=None):
        req = requests.get(get_url(path), headers=headers, params=params)

        json = req.json()

        if not json.get("result"):
            print(json)
            raise Exception("request failed")

        return json.get("result")

    def get_pair(self, pair: str) -> str:
        return "".join(pair.split("/"))

    def assets(self):
        return self._request("/assets")

    def asset(self, asset):
        return self._request(f"/assets/{asset}")

    def pairs(self):
        return self._request("/pairs")

    def pair(self, pair):
        return self._request(f"/pairs/{pair}")

    def markets(self):
        return self._request("/markets")

    def market(self, exchange, pair):
        return self._request(f"/markets/{exchange}/{pair}")

    def market_price(self, exchange, pair):
        return self._request(f"/markets/{exchange}/{pair}/price")

    def market_prices(self):
        return self._request("/markets/prices")

    def trades(self, exchange, pair, since=None, limit=100):
        return self._request(
            f"/market/{exchange}/{pair}/trades", params={"since": since, "limit": limit}
        )

    def summary(self, exchange, pair):
        return self._request(f"/markets/{exchange}/{pair}/summary")

    def summaries(self):
        return self._request("/markets/summaries")

    def order_book(self, exchange, pair):
        return self._request(f"/markets/{exchange}/{pair}/orderbook")

    def order_book_liquidity(self, exchange, pair):
        return self._request(f"/markets/{exchange}/{pair}/orderbook/liquidity")

    def candles(self, exchange, pair, before=None, after=None, periods=900):
        try:
            candles = self._request(
                f"/markets/{exchange}/{pair}/ohlc",
                params={"before": before, "after": after, "periods": periods},
            )[f"{periods}"]
        except Exception as e:
            candles = self._request(
                f"/markets/gateio/{pair}/ohlc",
                params={"before": before, "after": after, "periods": periods},
            )[f"{periods}"]

        df = pd.DataFrame(candles)
        df.columns = ["time", "open", "high", "low", "close", "volume", "quote_volume"]

        df["time"] = df["time"].apply(datetime.fromtimestamp)
        df.set_index("time", inplace=True)
        df = df.sort_values("time")

        return df

    def exchanges(self):
        return self._request("/exchanges")

    def exchange(self, exchange):
        return self._request(f"/exchanges/{exchange}")

    def exchange_markets(self, exchange):
        return self._request(f"/markets/{exchange}")

    def rsi(
        self,
        pair,
        exchange="coinbase-pro",
        span=14,
        type="day",
        before=None,
        after=None,
    ):
        df = self.candles(
            exchange, pair, periods=rsi_type[type], before=before, after=after
        )
        df["rsi"] = rsi(df["close"], span)

        return df

    def multi_rsi(self, pair):
        day = self.rsi(pair, type="day")
        week = self.rsi(pair, type="week")

        return {"day": day["rsi"].iloc[-1], "week": week["rsi"].iloc[-1]}

    def get_reference_price(self, exchange, pair, window_span=12):
        after = int(datetime.now().timestamp()) - int(
            timedelta(hours=window_span).total_seconds()
        )

        df = self.candles(exchange=exchange, pair=self.get_pair(pair), after=after)
        df["EWM"] = df["close"].ewm(span=window_span).mean()

        return df["EWM"].iloc[-1]

    def get_best_prices_from_orderbook(self, exchange, pair):
        orderbook = self.order_book(exchange, self.get_pair(pair))

        return {"ask": orderbook["asks"][0], "bid": orderbook["bids"][0]}


if __name__ == "__main__":
    client = CryptowatchClient()

    res = client.multi_rsi("linketh")
    print(res)
