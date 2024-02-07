from modules.database.db import DB
from modules.database.models import NotificationStatus


class NotificationDB(DB):
    @classmethod
    async def get_notification_status(cls, user_id: int) -> NotificationStatus:
        async with cls.pool.acquire() as connection:
            _ = await connection.fetchrow(
                "SELECT status, is_newbie_requested, is_update_requested, is_end_date, error_check_token FROM user_notification WHERE user_id = $1",
                user_id,
            )
            return NotificationStatus(*_)

    @classmethod
    async def set_notification_status(cls, user_id: int, key: str, state: bool) -> None:
        async with cls.pool.acquire() as connection:
            await connection.execute(f"UPDATE user_notification SET {key} = $1 WHERE user_id = $2", state, user_id)
