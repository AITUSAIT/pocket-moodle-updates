import aiohttp
from aiohttp import ClientResponse

from config import PM_TOKEN
from modules.base_api import BaseAPI
from modules.pm_api.models import User


class QueueAPI(BaseAPI):
    async def get_user_from_queue(self) -> User:
        params = {
            "token": PM_TOKEN,
        }
        response: ClientResponse = await self.get("/api/queue/user/", params=params)
        json_response = await response.json()
        return User.model_validate(json_response)

    async def insert_user_into_queue(self, user_id: int) -> None:
        params = {
            "token": PM_TOKEN,
            "user_id": user_id,
        }
        response: ClientResponse = await self.post("/api/queue/", params=params)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def log_queue_result(self, user_id: int, log: str) -> None:
        params = {
            "token": PM_TOKEN,
        }
        data = aiohttp.FormData(
            {
                "user_id": user_id,
                "log": log,
            }
        )
        response: ClientResponse = await self.post("/api/queue/log/", params=params, data=data)
        json_response = await response.json()
        assert json_response.get("success") is True
