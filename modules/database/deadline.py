import json
from datetime import datetime

from modules.database.db import DB
from modules.database.models import Deadline


class DeadlineDB(DB):
    pending_queries_deadlines = []

    @classmethod
    async def get_deadlines(cls, user_id: int, course_id: int) -> dict[str, Deadline]:
        async with cls.pool.acquire() as connection:
            deadlines = await connection.fetch(
                """
            SELECT
                d.id, d.assign_id, d.name, dp.due, dp.graded, dp.submitted, dp.status
            FROM
                deadlines d
            INNER JOIN
                deadlines_user_pair dp ON dp.id = d.id
            WHERE
                dp.user_id = $1 and d.course_id = $2
            """,
                user_id,
                course_id,
            )

            return {
                str(_[0]): Deadline(
                    id=_[0], assign_id=_[1], name=_[2], due=_[3], graded=_[4], submitted=_[5], status=json.loads(_[6])
                )
                for _ in deadlines
            }

    @classmethod
    def set_deadline(
        cls,
        user_id: int,
        course_id: int,
        deadline_id: int,
        assign_id: int,
        name: str,
        due: datetime,
        graded: bool,
        submitted: bool,
        status: dict,
    ):
        query = """
        INSERT INTO
            deadlines (id, assign_id, name, course_id)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT
            (id)
        DO NOTHING;
        """
        cls.add_query(query, deadline_id, assign_id, name, course_id)
        cls.set_deadline_user_pair(
            user_id=user_id, deadline_id=deadline_id, due=due, submitted=submitted, graded=graded, status=status
        )

    @classmethod
    def set_deadline_user_pair(
        cls, user_id: int, deadline_id: int, due: datetime, submitted: bool, graded: bool, status: dict
    ):
        query = """
        INSERT INTO
            deadlines_user_pair (user_id, id, submitted, graded, status, due)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        cls.add_query(query, user_id, deadline_id, submitted, graded, json.dumps(status), due)

    @classmethod
    def update_deadline(
        cls, user_id: int, deadline_id: int, name: str, due: datetime, graded: bool, submitted: bool, status: dict
    ):
        query = """
        UPDATE
            deadlines
        SET
            name = $1
        WHERE
            id = $2;
        """
        cls.add_query(query, name, deadline_id)
        query = """
        UPDATE
            deadlines_user_pair
        SET
            submitted = $1, graded = $2, status = $3, due = $4
        WHERE
            id = $5 and user_id = $6;
        """
        cls.add_query(query, submitted, graded, json.dumps(status), due, deadline_id, user_id)

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
