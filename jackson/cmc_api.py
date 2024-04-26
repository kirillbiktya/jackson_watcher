import httpx
from config import CMC_API_KEY
from typing import List, Union


class CMCAPI:
    def __init__(self):
        self.api_key = CMC_API_KEY

    def __make_request(self, endpoint: str, **kwargs):
        headers = {"X-CMC_PRO_API_KEY": self.api_key}
        response = httpx.get(
            "https://pro-api.coinmarketcap.com{}".format(endpoint),
            headers=headers,
            **kwargs
        )
        data = response.json()
        if data["status"]["error_code"] != 0:
            raise Exception(data["status"]["error_message"])

        return data["data"]

    def get_top10_coins(self):
        try:
            return self.__make_request("/v1/cryptocurrency/map", params={"sort": "cmc_rank", "limit": 10})
        except Exception as e:
            print(str(e))
            return []

    def get_coins_price(self, coin_ids: List[Union[int, str]]):
        try:
            return self.__make_request("/v2/cryptocurrency/quotes/latest", params={"id": ",".join(coin_ids)})
        except Exception as e:
            print(str(e))
            return {}
