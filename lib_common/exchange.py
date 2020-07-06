from enum import Enum
from typing import TypedDict


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class PriceType(Enum):
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    LIMIT_MARGIN = "LIMIT_MARGIN"
    STOP_LIMIT_MARGIN = "STOP_LIMIT_MARGIN"


class Order(TypedDict):
    id: int
    pair: str
    order_type: OrderType
    price_type: PriceType
    price: float
    amount: float
