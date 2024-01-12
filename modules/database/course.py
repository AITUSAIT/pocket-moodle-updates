from . import DeadlineDB 
from . import GradeDB 
from .models import Course


class CourseDB(DeadlineDB, GradeDB):
    pending_queries_courses = []

    @classmethod
    async def is_ready_courses(cls, user_id: int) -> bool:
        user = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            course_count = await connection.fetchval(
                f'SELECT COUNT(*) FROM courses INNER JOIN courses_user_pair cp ON cp.user_id = $1',
                user.user_id
            )
            return course_count > 0 
    
    @classmethod
    async def get_courses(cls, user_id: int, is_active: bool = None) -> dict[str, Course]:
        user = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            courses = await connection.fetch(f'''
            SELECT
                c.course_id, c.name, cp.active
            FROM
                courses c
            INNER JOIN
                courses_user_pair cp ON c.course_id = cp.course_id
            WHERE
                cp.user_id = $1
                AND (cp.active = $2 OR $2 IS NULL);
            ''', user.user_id, is_active)
            
            return { str(_[0]): Course(
                course_id=_[0],
                name=_[1],
                active=_[2],
                grades=(await cls.get_grades(user.user_id, _[0])),
                deadlines=(await cls.get_deadlines(user.user_id, _[0]))
            ) for _ in courses }

    @classmethod
    def set_course(cls, user_id: int, course_id: int, name: str, active: bool):
        query = f'''
        INSERT INTO
            courses (course_id, name)
        VALUES ($1, $2)
        ON CONFLICT
            (course_id)
        DO NOTHING;
        '''
        cls.add_query(query, course_id, name)
        cls.set_course_user_pair(
            user_id=user_id,
            course_id=course_id,
            active=active
        )
        
    @classmethod
    def set_course_user_pair(cls, user_id: int, course_id: int, active: bool):
        query = f'INSERT INTO courses_user_pair (user_id, course_id, active) VALUES ($1, $2, $3)'
        cls.add_query(query, user_id, course_id, active)
    
    @classmethod
    def update_course_user_pair(cls, user_id: int, course_id: int, active: bool):
        query = f'UPDATE courses_user_pair SET active = $1 WHERE course_id = $2 and user_id = $3'
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