import asyncio
from datetime import datetime, timedelta

import pandas as pd

from lib_common.exchange import Order, OrderType
from services.client_adapter import ClientAdapter
from services.loopring_client import LoopringClient


class Loopring(ClientAdapter):
    def __init__(self):
        self.client = LoopringClient()

    def get_pair(self, name: str):
        return "-".join(name.split("/")).upper()

    async def add_order(self, order: Order):
        token1, token2 = self.get_pair(order["pair"]).split("-")

        if order["order_type"] == OrderType.BUY:
            response = self.client.buy(
                token1, token2, order["price"], abs(order["amount"]),
            )

        else:
            response = self.client.sell(
                token1, token2, order["price"], abs(order["amount"]),
            )

        return {"id": response}

    async def cancel_order(self, order_id: int):
        self.client.cancel_order(order_hash=order_id)

        return {"id": order_id}

    async def get_orders(self, pair=None):
        data = self.client.get_orders()

        orders = [
            {
                "id": order["hash"],
                "symbol": pair,
                "status": order["status"],
                "pair": pair,
            }
            for order in data["orders"]
            if order["market"] == self.get_pair(pair)
        ]

        return orders

    async def get_balances(self):
        return self.client.get_balances()

    async def get_history(self, pair: str):
        orders = self.client.get_trades(self.get_pair(pair))

        orders = [
            {
                "external_id": order["tradeID"],
                "created_at": datetime.fromtimestamp(
                    int(order["trade_timestamp"]) / 1000
                ),
                "pair": pair,
                "price": order["price"],
                "amount": order["quote_volume"],
                "amount_filled": order["base_volume"],
                "type": order["type"],
            }
            for order in orders
        ]

        return orders

    async def get_best_prices_from_orderbook(self, pair=""):
        orderbook = self.client.get_orderbook(self.get_pair(pair), limit=1)

        return {"ask": orderbook["asks"][0][:2], "bid": orderbook["bids"][0][:2]}

    async def get_reference_price(self, exchange="", pair="", window_span=12):
        df = await self.get_candles(pair, interval="15min")
        df["EWM"] = df["close"].ewm(span=window_span).mean()

        return df["EWM"].iloc[-1]

    async def get_candles(self, pair="", interval="1d", window_span=14):
        start = int(datetime.now().timestamp()) - int(
            timedelta(days=window_span).total_seconds()
        )

        candles = self.client.get_candles(
            self.get_pair(pair), start=start, interval=interval
        )

        df = pd.DataFrame(candles)
        df.columns = [
            "time",
            "transaction",
            "open",
            "close",
            "high",
            "low",
            "volume",
            "quote_volume",
        ]
        df["time"] = df["time"].apply(lambda x: datetime.fromtimestamp(int(x) / 1000))
        df.set_index("time", inplace=True)
        df = df.sort_values("time")
        df["close"] = df["close"].astype(float)

        return df

    async def get_last(self, pair: str):
        orders = self.client.get_trade_history()
        orders = [
            order for order in orders["trades"] if order[5] == self.get_pair(pair)
        ]

        sell_order = 0
        buy_order = 0

        for order in orders:
            if order[2] == "SELL" and sell_order == 0:
                sell_order = float(order[4])

            if order[2] == "BUY" and buy_order == 0:
                buy_order = float(order[4])

        return sell_order, buy_order


if __name__ == "__main__":
    loopring = Loopring()

    asyncio.run(loopring.get_balances())
