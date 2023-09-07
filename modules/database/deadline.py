from datetime import datetime
import json

from . import UserDB
from .models import User, Deadline


class DeadlineDB(UserDB):
    pending_queries_deadlines = []

    @classmethod
    async def get_deadlines(cls, value, course_id: int) -> dict[str, Deadline]:
        user: User = await cls.get_user(value)

        async with cls.pool.acquire() as connection:
            deadlines = await connection.fetch(f'SELECT id, assign_id, name, due, graded, submitted, status FROM user_deadlines WHERE user_id = $1 and course_id = $2', user.user_id, course_id)

            return { str(_[0]): Deadline(
                id=_[0],
                assign_id=_[1],
                name=_[2],
                due=_[3],
                graded=_[4],
                submitted=_[5],
                status=json.loads(_[6])
            ) for _ in deadlines }

    @classmethod
    async def set_deadline(cls, user_id: int, course_id: int, id: int, assign_id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict):
        query = 'INSERT INTO user_deadlines (id, assign_id, name, due, graded, submitted, status, course_id, user_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)'
        cls.add_query(query, id ,assign_id, name, due, graded, submitted, json.dumps(status), course_id, user_id)

    @classmethod
    async def update_deadline(cls, user_id: int, course_id: int, id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict):
        query = 'UPDATE user_deadlines SET name = $1, due = $2, graded = $3, submitted = $4, status = $5 WHERE id = $6 and course_id = $7 and user_id = $8'
        cls.add_query(query, name, due, graded, submitted, json.dumps(status), id, course_id, user_id)

    @classmethod
    def add_query(cls, query, *params):
        cls.pending_queries_deadlines.append((query, params))

    @classmethod
    async def commit(cls):
        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                for query, params in cls.pending_queries_deadlines:
                    await connection.execute(query, *params)
        cls.pending_queries_deadlines.clear()
    