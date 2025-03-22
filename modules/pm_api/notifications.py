from aiohttp import ClientResponse

from modules.base_api import BaseAPI

from .models import NotificationStatus


class NotificationsAPI(BaseAPI):
    async def get_notification_status(self, user_id: int) -> NotificationStatus:
        response = await self.get(f"/api/notifications/{user_id}/")
        json_response = await response.json()
        return NotificationStatus.model_validate(json_response)

    async def set_notification_status(self, user_id: int, notification_status: NotificationStatus):
        response: ClientResponse = await self.post(f"/api/notifications/{user_id}/", json=notification_status.to_dict())
        json_response = await response.json()
        assert json_response.get("success") is True
