from aiohttp import ClientResponse

from modules.base_api import BaseAPI

from .models import Course


class CoursesAPI(BaseAPI):
    async def get_courses(self, user_id: int, is_active: bool | None = None) -> dict[str, Course]:
        params = {
            "user_id": user_id,
        }
        if is_active is not None:
            params["is_active"] = int(is_active)
        response = await self.get("/api/courses", params=params)

        json_response = await response.json()
        courses: dict[str, Course] = {}
        for key, value in json_response.items():
            courses[key] = Course.model_validate(value)

        return courses

    async def is_ready_courses(self, user_id: int) -> bool:
        response: ClientResponse = await self.get(f"/api/courses/is_ready_courses/{user_id}")
        json_response = await response.json()

        assert json_response.get("success") is True
        assert "response" in json_response
        assert "is_ready_courses" in json_response["response"]

        return json_response["response"]["is_ready_courses"]
