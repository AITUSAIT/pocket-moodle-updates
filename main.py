import asyncio
import json
import os
import time

import dotenv

from functions import aioredis
from functions.moodle import check_updates


dotenv.load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_DB = os.getenv('REDIS_DB')
REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASSWD = os.getenv('REDIS_PASSWD')

threads = int(os.getenv('THREADS'))
th_number = int(os.getenv('THREAD_NUMBER'))


async def run_check(user_id):
    user = await aioredis.redis.hgetall(user_id)
    try:
        user['courses'] = json.loads(user['courses'])
    except:
        ...

    result = await check_updates(user)
    if result == 0:
        print(f'{user_id} - Invalid Login ')
    elif result == -1:
        print(f'{user_id} - Error')
    elif result == 1:
        print(f'{user_id} - Success')
    else:
        print(f'{user_id} - {result}')


async def main():
    await aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    )
    while 1:
        start_time = time.time()
        keys : list = await aioredis.redis.keys()
        keys.remove('news')

        for i in range(0, len(keys)):
            if (i+th_number) % threads == 0 or th_number == 0:
                if await aioredis.is_registered_moodle(keys[i]):
                    os.environ["ATT_STATE"] = "1"
                    await run_check(keys[i])

        print(f"{(time.time() - start_time)} секунд\n")
    await aioredis.close()


asyncio.run(main())