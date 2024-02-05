from datetime import datetime, timedelta

from async_lru import alru_cache

from modules.database.db import DB
from modules.database.models import User


class UserDB(DB):
    @classmethod
    async def create_user(cls, user_id: int, api_token: str) -> None:
        user_data = (user_id, api_token, datetime.now())

        notification_data = [
            (user_id, True, False, True, False),
        ]

        settings_app_data = [
            (user_id, False, True, True),
        ]

        settings_bot_data = [
            (user_id, True, True, True),
        ]

        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                await connection.executemany(
                    "INSERT INTO users (user_id, api_token, register_date) VALUES ($1, $2, $3);", [user_data]
                )
                await connection.executemany(
                    "INSERT INTO user_notification (user_id, status, is_newbie_requested, is_update_requested, is_end_date) VALUES ($1, $2, $3, $4, $5);",
                    notification_data,
                )
                await connection.executemany(
                    "INSERT INTO user_settings_app (user_id, status, notification_grade, notification_deadline) VALUES ($1, $2, $3, $4);",
                    settings_app_data,
                )
                await connection.executemany(
                    "INSERT INTO user_settings_bot (user_id, status, notification_grade, notification_deadline) VALUES ($1, $2, $3, $4);",
                    settings_bot_data,
                )

        for func in [cls.get_user]:
            func.cache_invalidate(user_id)  # pylint: disable=no-member

    @classmethod
    @alru_cache(ttl=360)
    async def get_user(cls, user_id: int) -> User:
        async with cls.pool.acquire() as connection:
            user = await connection.fetchrow(
                "SELECT user_id, api_token, register_date, sub_end_date, mail FROM users WHERE user_id = $1", user_id
            )
            return User(*user) if user else None

    @classmethod
    @alru_cache(ttl=360)
    async def get_users(cls) -> list[User]:
        async with cls.pool.acquire() as connection:
            users = await connection.fetch("SELECT user_id, api_token, register_date, sub_end_date, mail FROM users")
            return [User(*user) for user in users]

    @classmethod
    async def register(cls, user_id: int, mail: str, api_token: str) -> None:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            await connection.execute(
                "UPDATE users SET api_token = $1, mail = $2 WHERE user_id = $3", api_token, mail, user.user_id
            )

        for func in [cls.get_user]:
            func.cache_invalidate(user_id)  # pylint: disable=no-member

    @classmethod
    async def if_msg_end_date(cls, user_id: int) -> bool:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            return await connection.fetchrow(
                "SELECT is_end_date FROM user_notification WHERE user_id = $1", user.user_id
            )

    @classmethod
    async def set_msg_end_date(cls, user_id: int, number: int) -> None:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            await connection.execute(
                "UPDATE user_notification SET is_end_date = $1 WHERE user_id = $2", number, user.user_id
            )

    @classmethod
    async def activate_sub(cls, user_id: int, days: int) -> None:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            if user:
                sub_end_date = user.sub_end_date
                new_sub_end_date = None
                if sub_end_date is None or sub_end_date < datetime.now():
                    new_sub_end_date = datetime.now() + timedelta(days=days)
                else:
                    new_sub_end_date = sub_end_date + timedelta(days=days)

                await connection.execute(
                    "UPDATE users SET sub_end_date = $1 WHERE user_id = $2", new_sub_end_date, user.user_id
                )
                cls.get_user.cache_invalidate(user_id)  # pylint: disable=no-member
