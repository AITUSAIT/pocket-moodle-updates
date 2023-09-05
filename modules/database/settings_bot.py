from . import UserDB
from .models import SettingBot, User


class SettingsBotDB(UserDB):
    @classmethod
    async def get_settings(cls, user_id: int) -> SettingBot:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            _ = await connection.fetchrow('SELECT status, notification_grade, notification_deadline FROM user_settings_bot WHERE user_id = $1', user.user_id)
            return SettingBot(*_)

    @classmethod
    async def set_setting(cls, user_id: int, key: str, state: bool) -> None:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            await connection.execute(f'UPDATE user_settings_bot SET {key} = $1 WHERE user_id = $2', state, user.user_id)
