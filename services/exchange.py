from asyncio.tasks import sleep
from datetime import datetime, timedelta
from enum import Enum
from typing import TypedDict

import pandas as pd

from lib_common.exchange import Order
from services.client_adapter import ClientAdapter
from services.cryptowatch_client import CryptowatchClient

max_tries = 4


class Exchange:
    def __init__(self, client: ClientAdapter, logger):
        self.client = client
        self.logger = logger

    async def create_order(self, order: Order):
        for i in range(max_tries):
            try:
                new_order = await self.client.add_order(order)
                return new_order

            except Exception as e:
                self.logger.exception(e)
                await sleep(2 ** i)

    async def cancel_order(self, order_id: int):
        for i in range(max_tries):
            try:
                canceled_order = await self.client.cancel_order(order_id)
                return canceled_order

            except Exception as e:
                self.logger.exception(e)
                await sleep(2 ** i)

    async def cancel_all_orders(self, pair):
        orders = await self.client.get_orders(pair)

        canceled_orders = []
        for order in orders:
            canceled_order = await self.cancel_order(order["id"])
            canceled_orders.append(canceled_order)

        return canceled_orders
