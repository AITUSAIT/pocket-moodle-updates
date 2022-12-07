import asyncio
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
        # await moodle.check()
        # print('>>>', "moodle.check()", time.time() - start, '\n')
        moodle.user.token_du = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJhdWQiOiJBc3RhbmFpdC5lZHUua3ogY2xpZW50Iiwic3ViIjoiNjU0MSIsImlzcyI6IkFzdGFuYWl0LmVkdS5reiBzZXJ2ZXIiLCJleHAiOjE2NzA0Mzg3MjYsImlhdCI6MTY3MDQzMTUyNiwiQ2xpZW50IGlwIjoiMTcyLjE5LjAuMTIifQ.6CM7CfToq9vqXiL6HJmQHhbJZgyGW37TMOGlXljLlJbnQtsxVOcRI6Ln8VnM_o8Q4lxmsypqEb5coi5c2xGKFA"
        moodle.user.login_status = True
        moodle.user.token = True
        if moodle.user.login_status and moodle.user.token:
            if moodle.user.token_du:
                await moodle.set_gpa(await moodle.get_gpa())

                curriculum = await moodle.get_curriculum(1)
                curriculum.extend(await moodle.get_curriculum(2))
                curriculum.extend(await moodle.get_curriculum(3))
                moodle.user.curriculum = {
                    '1': {'1': {}, '2': {}, '3': {}},
                    '2': {'1': {}, '2': {}, '3': {}},
                    '3': {'1': {}, '2': {}, '3': {}},
                }
                for id, component in enumerate(curriculum):
                    year = str(component['curriculum']['year'])
                    trimester = str(component['curriculum']['numberOfTrimester'])
                    discipline = {
                        'id': str(component['id']),
                        'name': component['curriculum']['discipline']['titleEn'],
                        'credits': component['curriculum']['discipline']['volumeCredits'],
                    }
                    moodle.user.curriculum[year][trimester][id] = discipline
                

            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


asyncio.run(check_updates(626591599))