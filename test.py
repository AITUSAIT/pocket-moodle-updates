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
from main import get_proxies
from moodle_module import Moodle, UserType


@timeit
async def check_updates(user_id):
    start = time.time()
    user: UserType = await aioredis.get_user(user_id)
    print('>>>', "get_user", time.time() - start, '\n')

    if user.is_registered_moodle:
        moodle = Moodle(user, {})
        res = await moodle.get_users_by_field('')
        print(res)
        await moodle.check()

        moodle.user.token = "asd"
        if moodle.user.login_status and moodle.user.token:
            value = await moodle.get_email()
            res = await moodle.get_users_by_field(value)
            print(res)
                

            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


asyncio.run(aioredis.start_redis(
    REDIS_USER,
    REDIS_PASSWD,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB
))
proxies = get_proxies()
asyncio.run(check_updates(626591599))