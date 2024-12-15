from typing import Any, Mapping

import aiohttp

from modules.singletone.metaclass import Singleton


class BaseAPI(metaclass=Singleton):
    host: str
    timeout: aiohttp.ClientTimeout

    async def get(
        self,
        end_point: str,
        params: Mapping[str, Any] | None = None,
        data: aiohttp.FormData | None = None,
    ):
        async with aiohttp.ClientSession(self.host, timeout=self.timeout) as session:
            return await session.get(end_point, params=params, data=data)

    async def post(
        self,
        end_point: str,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        data: aiohttp.FormData | None = None,
    ):
        async with aiohttp.ClientSession(self.host, timeout=self.timeout) as session:
            return await session.post(end_point, params=params, data=data, json=json)

    async def patch(
        self,
        end_point: str,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        data: aiohttp.FormData | None = None,
    ):
        async with aiohttp.ClientSession(self.host, timeout=self.timeout) as session:
            return await session.patch(end_point, params=params, data=data, json=json)

    async def delete(
        self,
        end_point: str,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        data: aiohttp.FormData | None = None,
    ):
        async with aiohttp.ClientSession(self.host, timeout=self.timeout) as session:
            return await session.delete(end_point, params=params, data=data, json=json)
