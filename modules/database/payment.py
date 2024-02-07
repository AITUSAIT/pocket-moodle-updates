from modules.database.db import DB
from modules.database.models import Transaction


class PaymentDB(DB):
    @classmethod
    async def create_payment(cls, transaction: Transaction) -> None:
        async with cls.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO user_payment (result, message, trackId, payLink, cost, months, user_id, message_id, user_mail) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                transaction["result"],
                transaction["message"],
                transaction["trackId"],
                transaction["payLink"],
                transaction["cost"],
                transaction["months"],
                transaction["user_id"],
                transaction["message_id"],
                transaction["user_mail"],
            )

    @classmethod
    async def get_payment(cls, user_id: int) -> Transaction:
        async with cls.pool.acquire() as connection:
            _ = await connection.fetchrow("SELECT * FROM user_payment WHERE user_id = $1", user_id)
            payment = {
                "result": _[1],
                "message": _[2],
                "trackId": _[3],
                "payLink": _[4],
                "cost": _[5],
                "months": _[6],
                "user_id": _[7],
                "message_id": _[8],
                "user_mail": _[9],
            }
            return Transaction(*payment)
