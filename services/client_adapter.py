from lib_common.exchange import Order
from services.cryptowatch_client import CryptowatchClient
from services.http import Http

data_feed = CryptowatchClient()


class ClientAdapter(Http):
    def get_pair(self, name: str):
        pass

    async def add_order(self, order: Order):
        pass

    async def cancel_order(self, order_id: int):
        pass

    async def get_orders(self, pair: str):
        pass

    async def get_balances(self):
        pass

    async def get_history(self, pair: str):
        pass

    async def get_last(self, pair: str):
        pass

    async def get_reference_price(self, exchange, pair, window_span=12):
        return data_feed.get_reference_price(exchange, pair, window_span)

    async def get_best_prices_from_orderbook(self, pair=""):
        pass

    async def get_candles(self, pair="", interval="1d", window_span=14):
        pass
