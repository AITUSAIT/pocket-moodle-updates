from datetime import datetime
import json

from . import UserDB
from .models import User, Deadline


class DeadlineDB(UserDB):
    pending_queries_deadlines = []

    @classmethod
    async def get_deadlines(cls, user_id: int, course_id: int) -> dict[str, Deadline]:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            deadlines = await connection.fetch(f'''
            SELECT
                d.id, d.assign_id, d.name, d.due, dp.graded, dp.submitted, dp.status
            FROM
                deadlines d
            INNER JOIN
                deadlines_user_pair dp ON dp.id = d.id
            WHERE
                dp.user_id = $1 and d.course_id = $2
            ''', user_id, course_id)

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
    def set_deadline(cls, user_id: int, course_id: int, id: int, assign_id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict):
        query = '''
        INSERT INTO
            deadlines (id, assign_id, name, due, course_id)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT
            (id)
        DO NOTHING;
        '''
        cls.add_query(query, id ,assign_id, name, due, course_id)
        cls.set_deadline_user_pair(user_id=user_id, id=id, submitted=submitted, graded=graded, status=status)

    @classmethod
    def set_deadline_user_pair(cls, user_id: int, id: int, submitted: bool, graded: bool, status: dict):
        query = f'''
        INSERT INTO
            deadlines_user_pair (user_id, id, submitted, graded, status)
        VALUES ($1, $2, $3, $4, $5)
        '''
        cls.add_query(query, user_id, id, submitted, graded, json.dumps(status))
    
    @classmethod
    def update_deadline(cls, user_id: int, id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict):
        query = '''
        UPDATE
            deadlines
        SET
            name = $1, due = $2
        WHERE
            id = $3;
        '''
        cls.add_query(query, name, due, id)
        query = '''
        UPDATE
            deadlines_user_pair
        SET
            submitted = $1, graded = $2, status = $3
        WHERE
            id = $4 and user_id = $5;
        '''
        cls.add_query(query, submitted, graded, json.dumps(status), id, user_id)
    
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
    