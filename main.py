import asyncio
import json
import os
import time

import aiohttp
import dotenv

from functions import aioredis
from functions.logger import logger
from functions.moodle import check_updates, send

dotenv.load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_DB = os.getenv('REDIS_DB')
REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASSWD = os.getenv('REDIS_PASSWD')

MAIN_HOST = os.getenv('MAIN_HOST')
token = os.getenv('token')

threads = int(os.getenv('THREADS'))
th_number = int(os.getenv('THREAD_NUMBER'))


async def run_check(user):
    user_id = user['user_id']
    try:
        user['courses'] = json.loads(user['courses'])
    except:
        ...

    result = await check_updates(user)

    if result == 0:
        res = 'Invalid Login'
        # if not await aioredis.check_if_msg(user_id):
        #     send(user_id, 'Invalid Login\nTry /register\_moodle to fix it')
    elif result == -1:
        res = 'Error'
    elif result == 1:
        res = 'Success'
    else:
        res = result
        # if not await aioredis.check_if_msg(user_id):
        #     send(user_id, result + '\nTry /register\_moodle to fix it')

    return res


async def main():
    await aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    )
    while 1:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{MAIN_HOST}/api/get_user/?token={token}&format=json') as response:
                data = await response.json()
            if response.status == 200:
                user = data['user']
                os.environ["ATT_STATE"] = "1"
                result = await run_check(user)
                params = {
                    'user_id': user['user_id'],
                    'result': result,
                }
                async with session.post(f'{MAIN_HOST}/api/update_user/?token={token}&format=json', data=params) as response:
                    logger.info(f"{user['user_id']} - {response.status}")
    await aioredis.close()


try:
    asyncio.run(main())
except Exception as exc:
    logger.error(exc, exc_info=True)
    logger.info('End')
