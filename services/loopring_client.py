import hashlib
import os
import urllib
from datetime import date, timedelta
from enum import Enum
from time import time
from typing import Any, Callable, Union

import requests

from ethsnarks.eddsa import PoseidonEdDSA
from ethsnarks.field import FQ, SNARK_SCALAR_FIELD
from ethsnarks.poseidon.permutation import poseidon, poseidon_params


class RequestStatus(Enum):
    ready = 0  # Request created
    success = 1  # Request successful (status code 2xx)
    failed = 2  # Request failed (status code not 2xx)
    error = 3  # Exception raised


class Request(object):
    def __init__(
        self,
        method: str,
        path: str,
        params: dict,
        data: Union[dict, str, bytes],
        headers: dict,
        callback: Callable = None,
        on_failed: Callable = None,
        on_error: Callable = None,
        extra: Any = None,
    ):
        self.method = method
        self.path = path
        self.callback = callback
        self.params = params
        self.data = data
        self.headers = headers

        self.on_failed = on_failed
        self.on_error = on_error
        self.extra = extra

        self.response = None
        self.status = RequestStatus.ready

    def __str__(self):
        if self.response is None:
            status_code = "terminated"
        else:
            status_code = self.response.status_code

        return (
            "request : {} {} {} because {}: \n"
            "headers: {}\n"
            "params: {}\n"
            "data: {}\n"
            "response:"
            "{}\n".format(
                self.method,
                self.path,
                self.status.name,
                status_code,
                self.headers,
                self.params,
                self.data,
                "" if self.response is None else self.response.text,
            )
        )


class Security(Enum):
    NONE = 0
    SIGNED = 1
    API_KEY = 2


account = {
    "exchangeName": "LoopringDEX: Beta 1",
    "exchangeAddress": "0x944644Ea989Ec64c2Ab9eF341D383cEf586A5777",
    "exchangeId": 2,
    "accountAddress": os.getenv("accountAddress"),
    "accountId": os.getenv("accountId"),
    "apiKey": os.getenv("apiKey"),
    "publicKeyX": os.getenv("publicKeyX"),
    "publicKeyY": os.getenv("publicKeyY"),
    "privateKey": os.getenv("privateKey"),
}

market_info_map = {
    "ETH": {"tokenId": 0, "symbol": "ETH", "decimals": 18},
    "LRC": {"tokenId": 2, "symbol": "LRC", "decimals": 18},
    "USDT": {"tokenId": 3, "symbol": "USDT", "decimals": 6},
    "DAI": {"tokenId": 5, "symbol": "DAI", "decimals": 18},
    "LINK": {"tokenId": 9, "symbol": "LINK", "decimals": 18},
    "KEEP": {"tokenId": 15, "symbol": "KEEP", "decimals": 18},
    "USDC": {"tokenId": 6, "symbol": "USDC", "decimals": 6},
    "DXD": {"tokenId": 16, "symbol": "DXD", "decimals": 18},
    "TRB": {"tokenId": 17, "symbol": "TRB", "decimals": 18},
    "AUC": {"tokenId": 18, "symbol": "AUC", "decimals": 18},
    "RPL": {"tokenId": 19, "symbol": "RPL", "decimals": 18},
    "WBTC": {"tokenId": 4, "symbol": "WBTC", "decimals": 8},
    "RENBTC": {"tokenId": 20, "symbol": "RENBTC", "decimals": 8},
    "PAX": {"tokenId": 21, "symbol": "PAX", "decimals": 18},
    "TUSD": {"tokenId": 22, "symbol": "TUSD", "decimals": 18},
    "MKR": {"tokenId": 7, "symbol": "MKR", "decimals": 18},
    "BUSD": {"tokenId": 23, "symbol": "BUSD", "decimals": 18},
}


class LoopringClient:
    MAX_ORDER_ID = 1_000_000

    url_base = "https://api.loopring.io"

    def __init__(self):

        self.api_key = account["apiKey"]
        self.exchangeId = account["exchangeId"]
        self.private_key = account["privateKey"].encode()
        self.address = account["accountAddress"]
        self.accountId = account["accountId"]
        self.publicKeyX = ""
        self.publicKeyY = ""

        self.orderId = [None] * 256
        self.time_offset = 0
        self.order_sign_param = poseidon_params(
            SNARK_SCALAR_FIELD, 14, 6, 53, b"poseidon", 5, security_target=128
        )

        self.query_time()
        for token_id in [info["tokenId"] for info in market_info_map.values()]:
            self.query_orderId(token_id)

    def get_full_url(self, path: str):
        return self.url_base + path

    def _encode_request(self, request):
        method = request.method
        url = urllib.parse.quote(self.url_base + request.path, safe="")
        data = urllib.parse.quote(
            "&".join([f"{k}={str(v)}" for k, v in request.params.items()]), safe=""
        )
        return "&".join([method, url, data])

    def sign(self, request):

        security = request.data["security"]

        if security == Security.NONE:
            if request.method == "POST":
                request.data = request.params
                request.params = {}
            return request

        if request.params:
            path = request.path + "?" + urllib.parse.urlencode(request.params)

        else:
            request.params = dict()
            path = request.path

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-API-KEY": self.api_key,
        }

        if security == Security.SIGNED:
            ordered_data = self._encode_request(request)
            hasher = hashlib.sha256()
            hasher.update(ordered_data.encode("utf-8"))
            msgHash = int(hasher.hexdigest(), 16) % SNARK_SCALAR_FIELD
            signed = PoseidonEdDSA.sign(msgHash, FQ(int(self.private_key)))
            signature = ",".join(
                str(_) for _ in [signed.sig.R.x, signed.sig.R.y, signed.sig.s]
            )
            headers.update({"X-API-SIG": signature})

        request.path = path
        if request.method != "GET":
            request.data = request.params
            request.params = {}
        else:
            request.data = {}

        request.headers = headers

        return request

    def request(
        self,
        method: str,
        path: str,
        params: dict = None,
        data: dict = None,
        headers: dict = None,
    ):
        request = Request(method, path, params, data, headers)

        request = self.sign(request)
        url = self.get_full_url(request.path)

        response = requests.request(
            request.method,
            url,
            headers=request.headers,
            params=request.params,
            data=request.data,
        )

        return response

    def query_time(self):
        data = {"security": Security.NONE}

        response = self.request("GET", path="/api/v2/timestamp", data=data)

        data = response.json()

        if data["resultInfo"]["code"] != 0:
            raise AttributeError(f"query_time failed {data}")

        local_time = int(time() * 1000)
        server_time = int(data["data"])
        self.time_offset = int((local_time - server_time) / 1000)

    def query_orderId(self, tokenId):
        data = {"security": Security.API_KEY}

        params = {"accountId": self.accountId, "tokenSId": tokenId}

        response = self.request(
            method="GET", path="/api/v2/orderId", params=params, data=data
        )

        data = response.json()

        if data["resultInfo"]["code"] != 0:
            raise AttributeError(f"query_orderId failed")

        tokenId = params["tokenSId"]
        self.orderId[tokenId] = int(data["data"])

    def query_server_time(self):
        data = {"security": Security.NONE}

        response = self.request("GET", path="/api/v2/timestamp", data=data)

        json_resp = response.json()

        if json_resp["resultInfo"]["code"] != 0:
            raise AttributeError(f"on_query_time failed {data}")

        return json_resp["data"]

    def buy(self, base_token, quote_token, price, volume):
        return self._order(base_token, quote_token, True, price, volume)

    def sell(self, base_token, quote_token, price, volume):
        self._order(base_token, quote_token, False, price, volume)

    def _serialize_order(self, order):
        return [
            int(order["exchangeId"]),
            int(order["orderId"]),
            int(order["accountId"]),
            int(order["tokenSId"]),
            int(order["tokenBId"]),
            int(order["amountS"]),
            int(order["amountB"]),
            int(order["allOrNone"] == "true"),
            int(order["validSince"]),
            int(order["validUntil"]),
            int(order["maxFeeBips"]),
            int(order["buy"] == "true"),
            int(order["label"]),
        ]

    def _order(self, base_token, quote_token, buy, price, volume):
        if buy:
            tokenS = market_info_map[quote_token]
            tokenB = market_info_map[base_token]
            amountS = str(int(10 ** tokenS["decimals"] * price * volume))
            amountB = str(int(10 ** tokenB["decimals"] * volume))

        else:
            tokenS = market_info_map[base_token]
            tokenB = market_info_map[quote_token]
            amountS = str(int(10 ** tokenS["decimals"] * volume))
            amountB = str(int(10 ** tokenB["decimals"] * price * volume))

        tokenSId = tokenS["tokenId"]
        tokenBId = tokenB["tokenId"]

        orderId = self.orderId[tokenSId]
        assert orderId < self.MAX_ORDER_ID
        self.orderId[tokenSId] += 1

        # 1 hour
        validSince = int(time()) - self.time_offset - 3600

        order = {
            "exchangeId": self.exchangeId,
            "orderId": orderId,
            "accountId": self.accountId,
            "tokenSId": tokenSId,
            "tokenBId": tokenBId,
            "amountS": amountS,
            "amountB": amountB,
            "allOrNone": "false",
            "validSince": validSince,
            "validUntil": validSince + (90 * 24 * 60 * 60),
            "maxFeeBips": 50,
            "label": 211,
            "buy": "true" if buy else "false",
            "clientOrderId": "SampleOrder" + str(int(time())),
        }

        order_message = self._serialize_order(order)
        msgHash = poseidon(order_message, self.order_sign_param)
        signedMessage = PoseidonEdDSA.sign(msgHash, FQ(int(self.private_key)))

        order.update(
            {
                "hash": str(msgHash),
                "signatureRx": str(signedMessage.sig.R.x),
                "signatureRy": str(signedMessage.sig.R.y),
                "signatureS": str(signedMessage.sig.s),
            }
        )

        data = {"security": Security.SIGNED}

        response = self.request(
            method="POST", path="/api/v2/order", params=order, data=data,
        )

        json_resp = response.json()

        if json_resp["resultInfo"]["code"] != 0:
            print(order)
            print(json_resp)
            raise AttributeError(f"order failed {data}")

        return json_resp["data"]

    def cancel_order(self, order_hash="", order_id=""):
        data = {"security": Security.SIGNED}
        params = {"accountId": self.accountId}

        if order_hash:
            params["orderHash"] = order_hash

        if order_id:
            params["clientOrderId"] = order_id

        response = self.request(
            method="DELETE", path="/api/v2/orders", params=params, data=data
        )

        json = response.json()

        if json["resultInfo"]["code"] != 0:
            raise AttributeError(f"cancel_order failed {json}")

        return json["data"]

    def get_orders(self, status="processing"):
        start = date.today() - timedelta(7)
        end = date.today() + timedelta(7)

        data = {"security": Security.SIGNED}
        params = {
            "accountId": self.accountId,
            "start": int(start.strftime("%s")) * 1000,
            "end": int(end.strftime("%s")) * 1000,
            "status": status,
        }

        response = self.request(
            method="GET", path="/api/v2/orders", params=params, data=data,
        )

        json = response.json()

        if json["resultInfo"]["code"] != 0:
            raise AttributeError(f"get_orders failed {response}")

        return json["data"]

    def get_token(self, token_id: str):
        for symbol in market_info_map:
            value = market_info_map[symbol]
            if value["tokenId"] == int(token_id):
                return symbol, value

    def get_token_by_name(self, token: str):
        for symbol in market_info_map:
            value = market_info_map[symbol]
            if value["tokenId"] == int(token_id):
                return symbol, value

    def get_balances(self):
        data = {"security": Security.SIGNED}

        response = self.request(
            method="GET",
            path="/api/v2/user/balances",
            params={"accountId": self.accountId},
            data=data,
        )

        data = response.json()["data"]

        balances = {}

        for balance in data:
            symbol, token = self.get_token(balance["tokenId"])
            amount = (int(balance["totalAmount"]) - int(balance["amountLocked"])) / (
                10 ** token["decimals"]
            )
            balances[symbol.lower()] = amount

        return balances

    def get_total_balances(self):
        data = {"security": Security.SIGNED}

        response = self.request(
            method="GET",
            path="/api/v2/user/balances",
            params={"accountId": self.accountId},
            data=data,
        )

        data = response.json()["data"]

        balances = {}

        for balance in data:
            symbol, token = self.get_token(balance["tokenId"])
            amount = (int(balance["totalAmount"])) / (10 ** token["decimals"])
            balances[symbol.lower()] = amount

        return balances

    def get_trades(self, market_pair, limit=1000):
        data = {"security": Security.SIGNED}

        params = {
            "accountId": self.accountId,
            "limit": limit,
            "market_pair": market_pair,
        }

        response = self.request(
            method="GET", path="/api/v2/trades", params=params, data=data,
        )

        return response.json()["data"]

    def get_orderbook(self, market_pair, level=1, limit=100):
        data = {"security": Security.API_KEY}

        params = {
            "market": market_pair,
            "level": level,
            "limit": limit,
        }

        response = self.request(
            method="GET", path="/api/v2/depth", params=params, data=data
        )

        return response.json()["data"]

    def get_candles(self, market_pair, interval="15min", start="", end="", limit=""):
        data = {"security": Security.API_KEY}

        params = {
            "market": market_pair,
            "interval": interval,
            "start": start,
            "end": end,
            "limit": limit,
        }

        response = self.request(
            method="GET", path="/api/v2/candlestick", params=params, data=data
        )

        json = response.json()

        if not json.get("data"):
            print(json)

        return json["data"]

    def get_trade_history(self, offset=0, limit=50):
        data = {"security": Security.API_KEY}

        params = {"accountId": self.accountId, "limit": limit, "offset": offset}

        response = self.request(
            method="GET", path="/api/v2/user/trades", params=params, data=data
        )

        return response.json()["data"]
