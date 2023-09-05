from datetime import datetime
from async_lru import alru_cache

from . import UserDB
from .models import User, Deadline


class DeadlineDB(UserDB):
    pending_queries = []

    @classmethod
    @alru_cache(ttl=5)
    async def get_deadlines(cls, value, course_id: int) -> dict[str, Deadline]:
        user: User = await cls.get_user(value)

        async with cls.pool.acquire() as connection:
            deadlines = await connection.fetch(f'SELECT id, assign_id, name, due, graded, submitted, status FROM user_deadlines WHERE user_id = $1 and course_id = $2', user.user_id, course_id)
            return { str(_[0]): Deadline(*_) for _ in deadlines }

    @classmethod
    async def set_deadline(cls, user_id: int, course_id: int, id: int, assign_id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict):
        query = 'INSERT INTO user_deadlines (id, assign_id, name, due, graded, submitted, status, course_id, user_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)'
        cls.add_query(query, id ,assign_id, name, due, graded, submitted, status, course_id, user_id)

    @classmethod
    async def update_deadline(cls, user_id: int, course_id: int, id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict):
        query = 'UPDATE user_deadlines SET name = $1 and due = $2 and graded = $3 and submitted = $4 and status = $5 WHERE id = $6 and course_id = $7 and user_id = $8'
        cls.add_query(query, name, due, graded, submitted, status, id, course_id, user_id)

    @classmethod
    def add_query(cls, query, *params):
        cls.pending_queries.append((query, params))

    @classmethod
    async def commit(cls):
        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                for query, params in cls.pending_queries:
                    await connection.execute(query, *params)
        cls.pending_queries.clear()
    