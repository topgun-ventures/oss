import os

import requests

default_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


class Http:
    base_url = ""

    def __init__(self, base_url="", headers={}):
        self.headers = {**default_headers, **headers}
        self.base_url = base_url

    def get_url(self, url):
        return self.base_url + url

    async def _request(self, method, path, headers={}, json=None, params=None):
        req = requests.request(
            method,
            self.get_url(path),
            headers={**self.headers, **headers},
            json=json,
            params=params,
        )
        return req.json()
