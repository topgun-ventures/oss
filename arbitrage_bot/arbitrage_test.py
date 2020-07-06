import functools
import logging.config
import math
import operator
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from time import sleep

import bellmanford as bf
import networkx as nx
import pandas as pd

from arbitrage_bot.config import config
from arbitrage_bot.constants import EXCHANGES, LOGS_DIR, SLEEP_TIME
from cryptowatch.cryptowatch import CryptoWatch
from lib_common.db_handle import insert_values
from multiprocessing import cpu_count

logger = logging.getLogger("main_logger")

os.makedirs(LOGS_DIR, exist_ok=True)

os.chdir(LOGS_DIR)

cw = CryptoWatch()


def get_inter_exchange_rates(
    wd_exchange_rates, wd_prices, ex, pairs, fees, other_exchanges
):

    all_coins = set(
        functools.reduce(operator.iconcat, [x.split("_") for x in pairs], [])
    )

    for c in all_coins:
        for oe in other_exchanges:
            ex_coin = f"{ex}_{c}"
            oe_coin = f"{oe}_{c}"

            wd_exchange_rates.append((ex_coin, oe_coin, {"weight": -math.log(fees[1])}))

            # For csv
            state_change = f"{ex}_{c}_{oe}_{c}"
            wd_prices[state_change] = fees[1]

    return wd_exchange_rates, wd_prices


def get_initial_data():
    wd_exchange_rates = []
    wd_prices = {}

    args = []

    for ex, exchange_info in EXCHANGES.items():
        fees = exchange_info["fees"]
        exchange_pairs = exchange_info["pairs"]

        wd_exchange_rates, wd_prices = get_inter_exchange_rates(
            wd_exchange_rates,
            wd_prices,
            ex,
            exchange_pairs,
            fees,
            [e for e in EXCHANGES if e != ex],
        )

        for p in exchange_pairs:
            args.append((ex, p, fees[0]))

    return wd_exchange_rates, wd_prices, args


def get_exchange_rates(values):

    exchange, ex_pair, fees = values
    coin, oc = ex_pair.split("/")

    best_prices = cw.get_best_prices_from_orderbook(exchange, pair)
    if not best_prices:
        logger.info(f"{exchange}, {pair} not taken")
        return [], {}

    # print(best_prices)

    best_buy_price = (1 - fees) / best_prices["ask"][0]
    best_sell_price = best_prices["bid"][0] * (1 - fees)
    # Para exchanges diferentes seria 1 / (best_ask * (1 + fee))

    coin_exchange = f"{exchange}_{coin}"
    oc_exchange = f"{exchange}_{oc}"

    exchange_rates = [
        (oc_exchange, coin_exchange, {"weight": -math.log(best_buy_price)}),
        (coin_exchange, oc_exchange, {"weight": -math.log(best_sell_price)}),
    ]

    # For csv
    state_change = f"{exchange}_{coin}_{exchange}_{oc}"
    reverse_state_change = f"{exchange}_{oc}_{exchange}_{coin}"

    prices = {
        state_change: best_sell_price,
        reverse_state_change: best_buy_price,
        f"{state_change}_vol": best_prices["bid"][1],
        f"{reverse_state_change}_vol": best_prices["ask"][1],
    }

    return exchange_rates, prices


def get_main_values(exchange_rates, prices, results):

    # time_now = datetime.now()
    for edges, res_prices in results:
        if not len(edges):
            return exchange_rates, prices

        exchange_rates += edges

        # med = datetime.now()
        prices = {**prices, **res_prices}

        # end_time = datetime.now()

        # print('middle', (med - time_now).total_seconds())
        # print('end', (end_time - med).total_seconds())

    # import sys
    # sys.exit()

    return exchange_rates, prices


def get_data(args, wd_exchange_rates, wd_prices):

    exchange_rates = wd_exchange_rates
    prices = wd_prices

    # t0 = datetime.now()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_exchange_rates, args)

        # t1 = datetime.now()

        # time_taken = (t1 - t0).total_seconds()
        exchange_rates, prices = get_main_values(exchange_rates, prices, results)

    return nx.DiGraph(exchange_rates), prices


def main():
    # Get Interexchange values
    wd_exchange_rates, wd_prices, args = get_initial_data()

    # t0 = datetime.now()
    # t1 = datetime.now()
    # dfs = []

    # while (t1 - t0).total_seconds() < 60 * 60 * 2:
    for n in iter(lambda: 0, 1):
        time_start = datetime.now()
        G, prices = get_data(args, wd_exchange_rates, wd_prices)

        # time_data = datetime.now()

        arb = bf.negative_edge_cycle(G)
        time_end = datetime.now()

        df = pd.DataFrame(prices, index=[0])
        df["timestamp"] = datetime.now()
        df["time_taken"] = (time_end - time_start).total_seconds()
        # df['time_taken_data'] = (time_data - time_start).total_seconds()
        # df['time_taken_algo'] = (time_end - time_data).total_seconds()

        df["arb"] = arb[2]
        if isinstance(arb[1], list):
            df["cycle"] = ", ".join(arb[1])

        # dfs.append(df)

        insert_values(df, "arbitrage")

        # t1 = datetime.now()

        sleep(SLEEP_TIME)

    # main_df = pd.concat(dfs, sort=False)
    # main_df.to_csv('arbitrage_sim.csv', index=False)


if __name__ == "__main__":
    logging.config.dictConfig(config["logger"])
    main()
