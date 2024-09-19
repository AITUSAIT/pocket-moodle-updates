from modules.base_api import BaseAPI

from .models import CourseContent


class CourseContentsAPI(BaseAPI):
    async def get_course_contents(self, course_id: int) -> dict[str, CourseContent]:
        response = await self.get(f"/api/course_contents/{course_id}/")

        json_response = await response.json()
        courses: dict[str, CourseContent] = {}
        for key, value in json_response.items():
            courses[key] = CourseContent.model_validate(value)

        return courses
