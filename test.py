import asyncio
from functions import aioredis
from functions.functions import timeit
from moodle_module import Moodle, UserType
from config import (MAIN_HOST, REDIS_DB, REDIS_HOST, REDIS_PASSWD, REDIS_PORT,
                    REDIS_USER, token)
from moodle_module.browser import Browser


@timeit
async def check_updates():
    browser = Browser()
                


asyncio.run(aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    ))
asyncio.run(check_updates())