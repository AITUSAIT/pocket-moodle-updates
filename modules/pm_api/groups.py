from aiohttp import ClientResponse

from modules.base_api import BaseAPI

from .models import Group


class GroupsAPI(BaseAPI):
    async def get_group(self, group_tg_id: int) -> Group:
        response = await self.get(f"/api/groups/{group_tg_id}/")
        json_response = await response.json()
        return Group.model_validate_json(json_response)

    async def create_group(self, group_tg_id: int, group_name: str):
        params = {
            "group_tg_id": group_tg_id,
            "group_name": group_name,
        }
        response: ClientResponse = await self.post("/api/groups/", params=params)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def register_user(self, group_tg_id: int, user_id: int):
        params = {
            "group_tg_id": group_tg_id,
            "user_id": user_id,
        }
        response: ClientResponse = await self.post(f"/api/groups/{group_tg_id}/register_user/", params=params)
        json_response = await response.json()
        assert json_response.get("success") is True
