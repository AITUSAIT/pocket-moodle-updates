from modules.base_api import BaseAPI

from .models import Deadline


class DeadlinesAPI(BaseAPI):
    async def get_deadlines(self, user_id: int, course_id: int) -> dict[str, Deadline]:
        params = {
            "user_id": user_id,
            "course_id": course_id,
        }
        response = await self.get("/api/deadlines/", params=params)

        json_response = await response.json()
        deadlines: dict[str, Deadline] = {}
        for key, value in json_response.items():
            deadlines[key] = Deadline.model_validate(value)

        return deadlines
