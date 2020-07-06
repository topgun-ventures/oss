import logging.config
import os
import sys
from asyncio.tasks import sleep
from datetime import datetime
from typing import TypedDict

from bot.clients import get_client
from bot.constants import LOGS_DIR
from lib_common.db import db
from lib_common.exchange import Order as GooseOrder
from lib_common.exchange import OrderType, PriceType
from models.exchange import Exchange
from models.order import Order
from models.pair import Pair
from services.exchange import Exchange as ExchangeProvider
from services.finance import rsi

logger = logging.getLogger("main_logger")
os.makedirs(LOGS_DIR, exist_ok=True)
os.chdir(LOGS_DIR)


def get_rsi_orders(candles, sell_price, buy_price, sell_balance, buy_balance, config):
    resistance = 45
    support = 55

    rsi_df = rsi(candles["close"], 14)
    current_rsi = rsi_df.iloc[-1]
    prev_rsi = rsi_df.iloc[-2]

    if (
        buy_balance > config.get("min_amount")
        and current_rsi > resistance
        and prev_rsi > resistance
    ):
        logger.info(
            f"{config['exchange']} - Rebalancing {buy_balance * buy_price}{config.get('coin_2')} into {config.get('coin_1')}"
        )
        return [(buy_price, buy_balance * 0.999)]

    if (
        sell_balance > config.get("min_amount")
        and current_rsi < support
        and prev_rsi < support
    ):
        logger.info(
            f"{config['exchange']} - Rebalancing {sell_balance}{config.get('coin_1')} into {config.get('coin_2')}"
        )
        return [(sell_price, -sell_balance * 0.999)]

    return []


class WeightsParams(TypedDict):
    type: str
    exp_constant: float
    descending: bool


class PriceDeviationParams(TypedDict):
    type: str
    step: float
    exp_constant_1: float
    exp_constant_2: float


class BotConfig(TypedDict):
    exchange: str
    provider: ExchangeProvider
    sleep_time: int
    min_amount: int
    fee: float
    pair: str
    pairs: any
    coin_1: str
    coin_2: str


default_config = BotConfig(sleep_time=30, min_amount=5, fee=0,)


class MarketBot:
    def __init__(self, config: BotConfig):
        self.config = {**default_config, **config}
        exchange_name = self.config.get("exchange")
        pair_name = "".join(self.config.get("pair").lower().split("/"))

        self.max_tries = 4
        self.client = get_client(exchange_name)
        self.provider = ExchangeProvider(client=self.client, logger=logger)

        self.exchange_id = Exchange.query.filter_by(name=exchange_name).first().id
        self.pair_id = Pair.query.filter_by(name=pair_name).first().id

    async def run(self):
        for _ in iter(lambda: 0, 1):
            logger.info(
                f"{self.config['exchange']} - Goose awakening - {self.config['pair']}"
            )

            await self.provider.cancel_all_orders(self.config["pair"])
            await self.create_all_orders()

            logger.info(
                f"{self.config['exchange']} - Goose going for a nap for {self.config['sleep_time']} seconds"
            )
            await sleep(self.config.get("sleep_time"))

    async def create_all_orders(self):
        balances = await self.client.get_balances()
        prices = await self.client.get_best_prices_from_orderbook(
            self.config.get("pair")
        )
        candles = await self.client.get_candles(self.config.get("pair"), interval="1d")

        sell_price = float(prices.get("bid")[0] or 0.0)
        buy_price = float(prices.get("ask")[0] or 0.0)

        sell_balance = balances.get(self.config.get("coin_1")) or 0.0
        buy_balance = balances.get(self.config.get("coin_2")) or 0.0

        print(buy_balance, buy_price)

        new_orders = (
            self.config.get("get_orders")(
                **{
                    "candles": candles,
                    "sell_price": sell_price,
                    "buy_price": buy_price,
                    "sell_balance": sell_balance,
                    "buy_balance": buy_balance / buy_price,
                    "config": self.config,
                }
            )
            or []
        )

        if len(new_orders) == 0:
            return

        for price, amount in new_orders:
            await self.create_an_order(price, amount)

        return len(new_orders)

    async def create_an_order(self, price, amount):
        for i in range(self.max_tries):
            try:
                external_order = await self.provider.create_order(
                    GooseOrder(
                        pair=self.config.get("pair"),
                        order_type=OrderType.BUY if amount > 0 else OrderType.SELL,
                        price_type=PriceType.LIMIT,
                        price=price,
                        amount=amount,
                    )
                )

                try:
                    order = Order(
                        exchange_id=self.exchange_id,
                        pair_id=self.pair_id,
                        order_exchange_id=external_order.get("id"),
                        amount=amount,
                        price=price,
                        timestamp=datetime.now(),
                    )

                    db.session.add(order)

                    logger.info(
                        f"{self.config['exchange']} - Created order {external_order['id']}"
                    )
                    return

                except Exception as e:
                    logger.exception(e)

            except Exception as e:
                sleep_time = 2 ** i
                logger.info(
                    "{} - Retrying order creation - waiting {} secs".format(
                        self.config.get("exchange"), sleep_time
                    )
                )
                logger.exception(e)
                await sleep(sleep_time)

        message = f"creating and order with parameters:{(price, amount)}"
        await self.shutdown(message)

    async def shutdown(self, message):
        logger.info(
            f"{self.config['exchange']} - Shutting down bot - More than {self.max_tries} in {message}"
        )
        logger.info(f"{self.config['exchange']} - Cancelling all active orders")

        await self.provider.cancel_all_orders(self.config.get("pair"))

        logger.info(f"{self.config['exchange']} - Goodbye")
        sys.exit()
