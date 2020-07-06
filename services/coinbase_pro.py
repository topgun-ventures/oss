import asyncio
import os

from lib_common.exchange import Order, OrderType
from services.client_adapter import ClientAdapter


class CoinbasePro(ClientAdapter):
    def __init__(self):
        # TODO: create own rest client
        self.client = None

    def get_pair(self, name: str):
        return "-".join(name.split("/")).upper()

    async def add_order(self, order: Order):
        if order["order_type"] == OrderType.BUY:
            order = self.client.buy(
                price=order["price"],
                size=abs(order["amount"]),
                order_type="limit",
                product_id=self.get_pair(order["pair"]),
            )

        else:
            order = self.client.sell(
                price=order["price"],
                size=abs(order["amount"]),
                order_type="limit",
                product_id=self.get_pair(order["pair"]),
            )

        return {"id": order["id"]}

    async def cancel_order(self, order_id: str):
        order = self.client.cancel_order(order_id)

        return {"id": order_id}

    async def get_orders(self, pair=None):
        orders = self.client.get_orders()
        return list(orders)

    async def get_balances(self):
        accounts = self.client.get_accounts()

        return {account.currency.lower(): account.balance for account in accounts}

    async def get_history(self, pair: str):
        pass
