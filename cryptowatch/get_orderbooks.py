import logging.config
import os
from time import sleep

from cryptowatch.config import config
from cryptowatch.constants import EXCHANGES, LOGS_DIR, SLEEP_TIME
from cryptowatch.cryptowatch import CryptoWatch
from lib_common.db_handle import query_to_frame

logger = logging.getLogger("main_logger")

os.makedirs(LOGS_DIR, exist_ok=True)

os.chdir(LOGS_DIR)

cw = CryptoWatch()


def get_all_orderbooks():
    for n in iter(lambda: 0, 1):
        logger.info("Awakening..")
        for ex, pairs in EXCHANGES.items():
            ex_id = query_to_frame(f"select id from exchanges where name = '{ex}'")[
                "id"
            ].iloc[0]
            for p in pairs:
                pair_id = query_to_frame(f"select id from pairs where name = '{p}'")[
                    "id"
                ].iloc[0]
                cw.insert_orderbook((ex_id, ex), (pair_id, p))

        logger.info(f"Going to sleep - see you in {SLEEP_TIME} seconds")
        sleep(SLEEP_TIME)


if __name__ == "__main__":
    logging.config.dictConfig(config["logger"])

    get_all_orderbooks()
