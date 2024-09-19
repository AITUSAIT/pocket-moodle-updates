from modules.base_api import BaseAPI

from .models import Grade


class GradesAPI(BaseAPI):
    async def get_grades(self, user_id: int, course_id: int) -> dict[str, Grade]:
        params = {
            "user_id": user_id,
            "course_id": course_id,
        }
        response = await self.get("/api/grades/", params=params)

        json_response = await response.json()
        grades: dict[str, Grade] = {}
        for key, value in json_response.items():
            grades[key] = Grade.model_validate(value)

        return grades
