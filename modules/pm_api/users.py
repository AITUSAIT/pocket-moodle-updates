from aiohttp import ClientResponse

from modules.base_api import BaseAPI

from .models import Course, Deadline, Grade, User


class UsersAPI(BaseAPI):
    async def get_user(self, user_id: int) -> User | None:
        response = await self.get(f"/api/users/{user_id}")
        if response.status == 404:
            return None

        json_response = await response.json()
        return User.model_validate(json_response)

    async def get_users(self) -> list[User]:
        response = await self.get("/api/users")
        json_response = await response.json()
        return [User.model_validate(data) for data in json_response]

    async def create_user(self, user_id: int):
        params = {
            "user_id": user_id,
        }
        response: ClientResponse = await self.post("/api/users", params=params)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def register_moodle(self, user_id: int, mail: str, api_token: str):
        params = {
            "user_id": user_id,
            "mail": mail,
            "api_token": api_token,
        }
        response: ClientResponse = await self.post(f"/api/users/{user_id}/register_moodle", params=params)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def link_user_with_course(self, user_id: int, course: Course):
        response: ClientResponse = await self.post(f"/api/users/{user_id}/course", json=course.to_dict())
        json_response = await response.json()
        assert json_response.get("success") is True

    async def update_user_link_with_course(self, user_id: int, course: Course):
        response: ClientResponse = await self.patch(f"/api/users/{user_id}/course", json=course.to_dict())
        json_response = await response.json()
        assert json_response.get("success") is True

    async def link_user_with_grade(self, user_id: int, course: Course, grade: Grade):
        data = {
            "course": course.to_dict(json_support=True),
            "grade": grade.to_dict(json_support=True),
        }
        response: ClientResponse = await self.post(f"/api/users/{user_id}/grade", json=data)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def update_user_link_with_grade(self, user_id: int, course: Course, grade: Grade):
        data = {
            "course": course.to_dict(json_support=True),
            "grade": grade.to_dict(json_support=True),
        }
        response: ClientResponse = await self.patch(f"/api/users/{user_id}/grade", json=data)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def link_user_with_deadline(self, user_id: int, course: Course, deadline: Deadline):
        data = {
            "course": course.to_dict(json_support=True),
            "deadline": deadline.to_dict(json_support=True),
        }
        response: ClientResponse = await self.post(f"/api/users/{user_id}/deadline", json=data)
        json_response = await response.json()
        assert json_response.get("success") is True

    async def update_user_link_with_deadline(self, user_id: int, course: Course, deadline: Deadline):
        data = {
            "course": course.to_dict(json_support=True),
            "deadline": deadline.to_dict(json_support=True),
        }
        response: ClientResponse = await self.patch(f"/api/users/{user_id}/deadline", json=data)
        json_response = await response.json()
        assert json_response.get("success") is True
