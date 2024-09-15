from aiohttp import ClientResponse

from modules.base_api import BaseAPI

from .models import SettingBot


class SettingsAPI(BaseAPI):
    async def get_settings(self, user_id: int) -> SettingBot:
        response = await self.get(f"/api/settings_bot/{user_id}")
        json_response = await response.json()
        return SettingBot.model_validate(json_response)

    async def set_settings(self, user_id: int, settings: SettingBot):
        response: ClientResponse = await self.post(f"/api/settings_bot/{user_id}", json=settings.to_dict())
        json_response = await response.json()
        assert json_response.get("success") is True
