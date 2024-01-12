from . import UserDB
from .models import Grade, User


class GradeDB(UserDB):
    pending_queries_grades = []

    @classmethod
    async def get_grades(cls, user_id, course_id: int) -> dict[str, Grade]:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            grades = await connection.fetch(f'SELECT grade_id, name, percentage FROM grades WHERE user_id = $1 and course_id = $2', user.user_id, course_id)
            return { str(_[0]): Grade(*_) for _ in grades }

    @classmethod
    async def set_grade(cls, user_id: int, course_id: int, grade_id: int, name: str, percentage: str):
        query = 'INSERT INTO grades (course_id, grade_id, user_id, name, percentage) VALUES ($1, $2, $3, $4, $5)'
        cls.add_query(query, course_id, grade_id, user_id, name, percentage)

    @classmethod
    async def update_grade(cls, user_id: int, course_id: int, grade_id: int, percentage: str):
        query = 'UPDATE grades SET percentage = $1 WHERE course_id = $2 and grade_id = $3 and user_id = $4'
        cls.add_query(query, percentage, course_id, grade_id, user_id)

    @classmethod
    def add_query(cls, query, *params):
        cls.pending_queries_grades.append((query, params))

    @classmethod
    async def commit(cls):
        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                for query, params in cls.pending_queries_grades:
                    await connection.execute(query, *params)
        cls.pending_queries_grades.clear()