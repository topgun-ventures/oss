import asyncio
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from bfxapi import Client
from bfxapi.models import Order as BfxOrder

from lib_common.exchange import Order, OrderType
from services.client_adapter import ClientAdapter

AFF_CODE = "PXahOd_dW"


class Bitfinex(ClientAdapter):
    def __init__(self):
        self.bfx = Client(
            API_KEY=os.getenv("BFX_API_KEY"),
            API_SECRET=os.getenv("BFX_API_SECRET"),
            logLevel="DEBUG",
        )

    def get_pair(self, name: str):
        return "t" + "".join(name.split("/")).upper()

    async def add_order(self, order: Order):
        response = await self.bfx.rest.submit_order(
            self.get_pair(order["pair"]),
            order["price"],
            order["amount"],
            market_type=BfxOrder.Type.EXCHANGE_LIMIT,
            aff_code=AFF_CODE,
        )

        if response.status != "SUCCESS":
            raise Exception("Order failed")

        return {"id": [response.notify_info[0].id]}

    async def cancel_order(self, order_id: int):
        response = await self.bfx.rest.submit_cancel_order(order_id)

        return {
            "amount_filled": [response.notify_info.amount_filled],
            "status": [response.status],
            "id": [order_id],
        }

    async def get_orders(self, pair: str):
        active_orders = await self.bfx.rest.get_active_orders(self.get_pair(pair))

        return [
            {
                "id": order.id,
                "symbol": order.symbol,
                "status": order.status,
                "pair": pair,
            }
            for order in active_orders
        ]

    async def get_balances(self):
        wallets = await self.bfx.rest.get_wallets()

        return {w.currency.lower(): w.balance for w in wallets}

    async def get_history(self, pair: str):
        orders = await self.bfx.rest.get_order_history(
            self.get_pair(pair), start=0, end=datetime.now(), limit=1000
        )
        orders = [
            {
                "external_id": order.id,
                "created_at": datetime.fromtimestamp(order.mts_create / 1000),
                "updated_at": datetime.fromtimestamp(order.mts_update / 1000),
                "pair": pair,
                "price": order.price,
                "amount": order.amount,
                "amount_filled": order.amount_filled,
                "type": order.type,
                "status": order.status,
            }
            for order in orders
            if order.status != "CANCELED"
        ]
        return orders

    async def get_last(self, pair: str):
        end = datetime.now()
        start = end - timedelta(days=3)
        orders = await self.bfx.rest.get_order_history(
            self.get_pair(pair), start=start, end=end, limit=1000
        )

        sell_order = 0
        buy_order = 0

        for order in orders:
            if "EXECUTED" in order.status:
                if order.amount_filled < 0 and sell_order == 0:
                    sell_order = order.price

                if order.amount_filled > 0 and buy_order == 0:
                    buy_order = order.price

        return sell_order, buy_order


if __name__ == "__main__":
    bfx = Bitfinex()

    asyncio.run(bfx.get_last("dai/usd"))
