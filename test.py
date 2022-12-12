import asyncio
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from pprint import pprint
import time

from config import (MAIN_HOST, REDIS_DB, REDIS_HOST, REDIS_PASSWD, REDIS_PORT,
                    REDIS_USER, token)
from functions import aioredis
from functions.bot import send
from functions.functions import timeit
from moodle_module import Moodle, UserType


@timeit
async def check_updates(user_id):
    start = time.time()
    
    await aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    )
    user: UserType = await aioredis.get_user(user_id)
    print('>>>', "get_user", time.time() - start, '\n')

    if user.is_registered_moodle:
        moodle = Moodle(user)
        await moodle.check()

        if moodle.user.login_status and moodle.user.token:
            courses = await moodle.get_courses()
            active_courses_ids = await moodle.get_active_courses_ids()
            for course in courses:
                ...
                

            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


asyncio.run(check_updates(626591599))