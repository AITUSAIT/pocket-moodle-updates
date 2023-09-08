from async_lru import alru_cache

from . import DeadlineDB 
from . import GradeDB 
from .models import Course


class CourseDB(DeadlineDB, GradeDB):
    pending_queries_courses = []

    @classmethod
    @alru_cache(ttl=5)
    async def is_ready_courses(cls, user_id: int) -> bool:
        user = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            course_count = await connection.fetchval(
                f'SELECT COUNT(*) FROM user_courses WHERE user_id = $1',
                user.user_id
            )
            return course_count > 0 
    
    @classmethod
    @alru_cache(ttl=5)
    async def get_courses(cls, user_id: int, is_active: bool = None) -> dict[str, Course]:
        user = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            courses = await connection.fetch(f'SELECT course_id, name, active FROM user_courses WHERE user_id = $1 AND (active = $2 OR $2 IS NULL)', user.user_id, is_active)
            return { str(_[0]): Course(
                course_id=_[0],
                name=_[1],
                active=_[2],
                grades=await cls.get_grades(user.user_id, _[0]),
                deadlines=await cls.get_deadlines(user.user_id, _[0])
            ) for _ in courses }

    @classmethod
    @alru_cache(ttl=5)
    async def get_course(cls, user_id: int, course_id: int) -> Course:
        async with cls.pool.acquire() as connection:
            row = await connection.fetchrow(f'SELECT id, course_id, name, active FROM user_courses WHERE user_id = $1 and course_id = $2', user_id, course_id)
            return Course(id=row[0], course_id=row[1], name=row[2], active=row[3], grades=await cls.get_grades(user_id, row[0]), deadlines=await cls.get_deadlines(user_id, row[0])) if row else None
    
    @classmethod
    async def set_course(cls, user_id: int, course_id: int, name: str, active: bool):
        query = f'INSERT INTO user_courses (course_id, name, active, user_id) VALUES ($1, $2, $3, $4)'
        cls.add_query(query, course_id, name, active, user_id)
    
    @classmethod
    async def update_course(cls, user_id: int, course_id: int, active: bool):
        query = f'UPDATE user_courses SET active = $1 WHERE course_id = $2 and user_id = $3'
        cls.add_query(query, active, course_id, user_id)
    
    @classmethod
    def add_query(cls, query, *params):
        cls.pending_queries_courses.append((query, params))

    @classmethod
    async def commit(cls):
        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                for query, params in cls.pending_queries_courses:
                    await connection.execute(query, *params)
        cls.pending_queries_courses.clear()