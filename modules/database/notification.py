from . import UserDB
from .models import NotificationStatus, User


class NotificationDB(UserDB):
    @classmethod
    async def get_notification_status(cls, user_id: int) -> NotificationStatus:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            _ = await connection.fetchrow('SELECT status, is_newbie_requested, is_update_requested, is_end_date FROM user_notification WHERE user_id = $1', user.user_id)
            return NotificationStatus(*_)

    @classmethod
    async def set_notification_status(cls, user_id: int, key: str, state: bool) -> None:
        user: User = await cls.get_user(user_id)

        async with cls.pool.acquire() as connection:
            await connection.execute(f'UPDATE user_notification SET {key} = $1 WHERE user_id = $2', state, user.user_id)
