import random
import string

from modules.database.db import DB


class PromocodeDB(DB):
    @classmethod
    async def get_promocode(cls, code: str) -> dict | None:
        async with cls.pool.acquire() as connection:
            _ = await connection.fetchrow(
                "SELECT code, days, count_of_usage, usage_settings, users FROM promocodes WHERE code = $1", code
            )
            return (
                {"code": _[0], "days": _[1], "count_of_usage": _[2], "usage_settings": _[3], "users": _[4]}
                if _
                else None
            )

    @classmethod
    async def add_promocode(cls, promocode: dict) -> None:
        async with cls.pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO public.promocodes 
                                     (code, days, count_of_usage, usage_settings, users) 
                                     VALUES($1, $2, $3, $4, $5)""",
                promocode["code"],
                promocode["days"],
                promocode["count_of_usage"],
                promocode["usage_settings"],
                promocode["users"],
            )

    @classmethod
    async def add_user_to_promocode(cls, code: str, user_id: int) -> None:
        async with cls.pool.acquire() as connection:
            await connection.execute(
                "UPDATE promocodes SET users = array_append(users, $1), count_of_usage = count_of_usage - 1 WHERE code = $2",
                str(user_id),
                code,
            )

    @classmethod
    async def generate_promocode(cls) -> str:
        code_length = 10
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
            existing_promocode = await cls.get_promocode(code)
            if not existing_promocode:
                return code
