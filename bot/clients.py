from services.bitfinex import Bitfinex
from services.client_adapter import ClientAdapter
from services.loopring import Loopring

clients = {"bitfinex": Bitfinex(), "loopring": Loopring()}


def get_client(name: str) -> ClientAdapter:
    return clients.get(name)
