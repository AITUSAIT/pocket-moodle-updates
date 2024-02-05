import asyncpg


class DB:
    pool: asyncpg.Pool

    @classmethod
    async def connect(cls, dsn):
        cls.pool = await asyncpg.create_pool(dsn)

    @classmethod
    async def close(cls):
        await cls.pool.close()
