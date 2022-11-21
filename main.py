import asyncio
import os
import threading

import aiohttp

from config import (MAIN_HOST, REDIS_DB, REDIS_HOST, REDIS_PASSWD, REDIS_PORT,
                    REDIS_USER, token)
from functions import aioredis
from functions.functions import clear_MD
from functions.logger import logger
from functions.moodle import check_updates, send
from server.module import run_server


async def run_check(user) -> str:
    result = await check_updates(user['user_id'])

    if result == 0:
        res = 'Invalid Login'
        if not await aioredis.check_if_msg(user['user_id']):
            await send(user['user_id'],'Invalid login or password\n/register\_moodle to fix')
    elif result == -1:
        res = 'Error'
    elif result == 1:
        res = 'Success'
    else:
        res = result
        if not await aioredis.check_if_msg(user['user_id']):
            await send(user['user_id'], clear_MD(result))

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
        user = {}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{MAIN_HOST}/api/get_user?token={token}', ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        user = data['user']
                        os.environ["ATT_STATE"] = "1"
                        result = await run_check(user)
                        params = {
                            'user_id': user['user_id'],
                            'result': result,
                        }
                        async with session.post(f'{MAIN_HOST}/api/update_user?token={token}', data=params, ssl=False) as response:
                            logger.info(f"{user['user_id']} - {response.status}")
                    else:
                        await asyncio.sleep(5)
        except Exception as exc:
            params = {
                'user_id': user['user_id'],
                'result': 'Error',
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{MAIN_HOST}/api/update_user?token={token}', data=params, ssl=False) as response:
                    logger.error(f"{user.get('user_id', None)} {exc}", exc_info=True)
            await asyncio.sleep(5)

    await aioredis.close()


threading.Thread(target=run_server, args=(), daemon=True).start()

asyncio.run(main())
