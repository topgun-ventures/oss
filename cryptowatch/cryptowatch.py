import logging.config
import os
from datetime import datetime
from time import sleep

import pandas as pd
import requests

from cryptowatch.config import config
from cryptowatch.constants import (
    CRPW_MARKETS,
    CRPW_ORDERBOOK_URL,
    CRPW_TRADES_URL,
    LOGS_DIR,
)
from lib_common.db_handle import insert_values

# from constants import CRPW_ORDERBOOK_URL


logger = logging.getLogger("main_logger")

os.makedirs(LOGS_DIR, exist_ok=True)

os.chdir(LOGS_DIR)


class CryptoWatch(object):
    def __init__(self):
        pass

    def get_orderbook(self, exchange_info, pair_info, asks=True, bids=True):
        url = CRPW_ORDERBOOK_URL.format(exchange_info[1], pair_info[1])
        resp = requests.get(url)
        orderbook = resp.json()["result"]

        ts = datetime.now()

        ask_df = pd.DataFrame()
        bid_df = pd.DataFrame()
        if asks:
            ask_df = pd.DataFrame(orderbook["asks"])
            ask_df.columns = ["price", "amount"]
            ask_df["timestamp"] = ts
            ask_df["exchange_id"] = exchange_info[0]
            ask_df["pair_id"] = pair_info[0]
        if bids:
            bid_df = pd.DataFrame(orderbook["bids"])
            bid_df.columns = ["price", "amount"]
            bid_df["timestamp"] = ts

            bid_df["exchange_id"] = exchange_info[0]
            bid_df["pair_id"] = pair_info[0]

        return {"ask": ask_df, "bid": bid_df}

    def insert_orderbook(self, exchange, pair):
        for i in range(20):
            try:
                dfs = self.get_orderbook(exchange, pair)

                for table, df in dfs.items():
                    table_name = f"{table}_orderbooks"
                    insert_values(df, table_name)
                    # logger.info(f"Inserted in {table_name}")

                return
            except Exception as e:
                sleep_time = 2 ** i
                logger.info("Retrying orderbook - waiting {} secs".format(sleep_time))
                logger.exception(e)
                sleep(sleep_time)
        return

    def get_best_prices_from_orderbook(self, exchange, pair):

        url = CRPW_ORDERBOOK_URL.format(exchange, pair)
        resp = requests.get(url).json()

        if "error" in resp.keys():
            return {}

        orderbook = resp["result"]

        return {"ask": orderbook["asks"][0], "bid": orderbook["bids"][0]}

    def get_trades(self, exchange, pair):

        url = CRPW_TRADES_URL.format(exchange, pair)
        resp = requests.get(url)
        trades = resp.json()["result"]

        df = pd.DataFrame(trades)

        df.columns = ["id", "timestamp", "price", "amount"]

        df["exchange_id"] = exchange
        df["pair_id"] = pair

        return df[[x for x in df.columns if x != "id"]]

    def insert_trades(self, exchange, pair, table_name="exchange_trades"):
        for i in range(20):
            try:
                df = self.get_trades(exchange, pair)

                insert_values(df, table_name)
                # logger.info(f"Inserted in {table_name}")

                return
            except Exception as e:
                sleep_time = 2 ** i
                logger.info("Retrying orderbook - waiting {} secs".format(sleep_time))
                logger.exception(e)
                sleep(sleep_time)
        return

    def get_markets(self):

        resp = requests.get(CRPW_MARKETS).json()["result"]
        df = pd.DataFrame(resp)

        dfs = {}
        for name in ["exchange", "pair"]:
            temp_df = df[[name]].drop_duplicates().reset_index()
            temp_df["id"] = temp_df.index + 1
            temp_df = temp_df[["id", name]]
            temp_df.columns = ["id", "name"]
            dfs[name + "s"] = temp_df

        return dfs

    def insert_markets(self):
        dfs = self.get_markets()

        for table, df in dfs.items():
            df["timestamp"] = datetime.now()
            # insert_values(df, table)
            df.to_csv(table + ".csv", index=False)
            logger.info(f"{table} inserted :)")


if __name__ == "__main__":
    logging.config.dictConfig(config["logger"])

    cw = CryptoWatch()

    # ask_df, bid_df = get_orderbook('kraken', 'dai', 'usdt')
    dfs = cw.get_markets()
    prices = cw.get_best_prices_from_orderbook("binance", "btcusd")
    breakpoint()
