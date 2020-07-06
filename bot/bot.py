import logging.config
import os
import sys
from asyncio.tasks import sleep
from datetime import datetime
from typing import TypedDict

import pandas as pd

from bot.clients import get_client
from bot.constants import LOGS_DIR
from bot.strategies import get_strategy
from lib_common.db import db
from lib_common.db_handle import insert_values, query_to_frame
from lib_common.exchange import Order as GooseOrder
from lib_common.exchange import OrderType, PriceType
from models.exchange import Exchange
from models.order import Order
from models.pair import Pair
from models.reference_price import ReferencePrice
from services.exchange import Exchange as ExchangeProvider

logger = logging.getLogger("main_logger")
os.makedirs(LOGS_DIR, exist_ok=True)
os.chdir(LOGS_DIR)


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
    strategy: str
    # max balanced used for sell and buy, [token1_balance, token2_balance]
    max_balance: list
    provider: ExchangeProvider
    sleep_time: int
    # minimum order amount in USD
    min_amount: int
    fee: float
    minimum_profit: float
    n_orders: int
    ref_price_await_time: int
    pair: str
    pairs: any
    coin_1: str
    coin_2: str
    weights_params: WeightsParams
    price_deviation_params: PriceDeviationParams


default_config = BotConfig(
    sleep_time=15,
    min_amount=2,
    max_balance=[float("inf"), float("inf")],
    minimum_profit=0.0005,
    n_orders=5,
    fee=0,
    ref_price_await_time=3600 * 4,
    weights_params=WeightsParams(type="exp", exp_constant=0.65, descending=True),
    price_deviation_params=PriceDeviationParams(
        type="exp", exp_constant_1=0.001, exp_constant_2=0.63, step=0.04,
    ),
)


class Bot:
    def __init__(self, config: BotConfig):
        self.max_tries = 4
        self.pr_window_span = 12

        self.config = {**default_config, **config}
        self.client = get_client(self.config["exchange"])
        self.provider = ExchangeProvider(client=self.client, logger=logger)

        self.last_total_orders = 2 * self.config["n_orders"]
        self.last_order_creation_time = datetime(1986, 6, 29, 0, 0, 0)

        self.strategy = get_strategy(
            self.config["strategy"],
            weights_params=self.config["weights_params"],
            price_deviation_params=self.config["price_deviation_params"],
        )

        exchange_name = self.config["exchange"]
        pair_name = "".join(self.config["pair"].lower().split("/"))
        self.exchange_id = Exchange.query.filter_by(name=exchange_name).first().id
        self.pair_id = Pair.query.filter_by(name=pair_name).first().id

    async def run(self):
        for _ in iter(lambda: 0, 1):
            logger.info(
                f"{self.config['exchange']} - Goose awakening - {self.config['pair']}"
            )

            active_orders = await self.check_active_orders()

            has_executed_order = len(active_orders) != self.last_total_orders

            has_time_expired = (
                datetime.now() - self.last_order_creation_time
            ).total_seconds() > self.config["ref_price_await_time"]

            log_part = "after a period of hard work"
            if has_executed_order or has_time_expired:
                await self.provider.cancel_all_orders(self.config["pair"])

                self.last_total_orders = await self.create_all_orders()

                self.last_order_creation_time = datetime.now()

            else:
                log_part = "after doing nothing"

            logger.info(
                f"{self.config['exchange']} - Goose going for a nap for {self.config['sleep_time']} seconds {log_part}"
            )
            await sleep(self.config["sleep_time"])

    async def create_all_orders(self):
        reference_price = await self.client.get_reference_price(
            exchange=self.config["exchange"], pair=self.config["pair"],
        )
        last_sell_order, last_buy_order = await self.client.get_last(
            self.config["pair"]
        )
        last_sell_order = last_sell_order or reference_price
        last_buy_order = last_buy_order or reference_price

        fee = self.config["fee"]
        min_profit = self.config["minimum_profit"]

        min_sell_price = last_buy_order * (1 + fee + min_profit)
        max_buy_price = last_sell_order / (1 + fee + min_profit)

        self.save_reference_price(reference_price)

        balances = await self.get_all_balances()

        sell_balance = balances.get(self.config["coin_1"]) or 0.0
        buy_balance = balances.get(self.config["coin_2"]) or 0.0

        sell_balance = min(sell_balance, self.config["max_balance"][0])
        buy_balance = min(buy_balance, self.config["max_balance"][1])

        new_orders = (
            self.strategy.get_orders(
                self.config["n_orders"],
                reference_price,
                sell_balance,
                buy_balance / reference_price,
                self.config["min_amount"] / reference_price,
                min_sell_price,
                max_buy_price,
                fee,
                min_profit,
            )
            or []
        )

        if len(new_orders) == 0:
            return logger.info(
                f"{self.config['exchange']} - Orders were not created. Please check minimum prices/amounts"
            )

        for price, amount in new_orders:
            await self.create_an_order(price, amount)

        return len(new_orders)

    async def create_an_order(self, price, amount):
        for i in range(self.max_tries):
            try:
                external_order = await self.provider.create_order(
                    GooseOrder(
                        pair=self.config["pair"],
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
                        order_exchange_id=external_order["id"],
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
                        self.config["exchange"], sleep_time
                    )
                )
                logger.exception(e)
                await sleep(sleep_time)

        message = f"creating and order with parameters:{(price, amount)}"
        await self.shutdown(message)

    async def get_all_balances(self):
        for i in range(self.max_tries):
            try:
                balances = await self.client.get_balances()
                df = pd.DataFrame(balances, index=[0]).T.reset_index()
                df.columns = ["symbol", "balance"]
                df["timestamp"] = datetime.now()
                df["exchange_id"] = self.exchange_id

                self.insert_new_balances(df)

                return balances

            except Exception as e:
                sleep_time = 2 ** i
                logger.info(
                    "{} - Retrying getting balances - waiting {} secs".format(
                        self.config["exchange"], sleep_time
                    )
                )
                logger.exception(e)
                await sleep(sleep_time)

        message = f"getting balances"
        await self.shutdown(message)

    async def check_active_orders(self):
        for i in range(self.max_tries):
            try:
                active_orders = await self.client.get_orders(self.config["pair"])

                logger.info(
                    f"{self.config['exchange']} - Checked exchange - {len(active_orders)} active orders"
                )

                return active_orders

            except Exception as e:
                sleep_time = 2 ** i
                logger.info(
                    "Retrying checking active orders - waiting {} secs".format(
                        sleep_time
                    )
                )
                logger.exception(e)
                await sleep(sleep_time)

            message = f"checking active orders"
            await self.shutdown(message)

    def save_reference_price(self, reference_price):
        price = ReferencePrice(
            exchange_id=self.exchange_id,
            pair_id=self.pair_id,
            av_price=reference_price,
            timestamp=datetime.now(),
        )
        db.session.add(price)

    def insert_new_balances(self, df):
        last_balance_query = f"""SELECT symbol,
                    LAST_VALUE(balance) OVER (PARTITION BY symbol ORDER BY timestamp) as last_balance,
                    timestamp
                    FROM balances
                    where exchange_id = {self.exchange_id}
                    """

        last_balance = query_to_frame(last_balance_query)

        if last_balance.empty:
            return None

        merged_df = pd.merge(df, last_balance, how="outer").fillna(0)

        new_balances = merged_df[merged_df["balance"] != merged_df["last_balance"]]

        if not new_balances.empty:
            insert_values(new_balances[["symbol", "balance", "timestamp"]], "balances")

    async def shutdown(self, message):
        logger.info(
            f"{self.config['exchange']} - Shutting down bot - More than {self.max_tries} in {message}"
        )
        logger.info(f"{self.config['exchange']} - Cancelling all active orders")

        await self.provider.cancel_all_orders(self.config["pair"])

        logger.info(f"{self.config['exchange']} - Goodbye")
        sys.exit()
