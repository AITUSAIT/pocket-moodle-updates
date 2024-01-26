import asyncio
import os
import threading
import traceback
from itertools import cycle

import aiohttp
from aiohttp import web

from config import (DB_DB, DB_HOST, DB_PASSWD, DB_PORT, DB_USER,
                    IS_UPDATE_CONTENT, MAIN_HOST, token)
from functions.moodle import check_updates
from functions.moodle_contents import update_course_contents
from modules.database import DB, ServerDB
from modules.logger import Logger

Logger.load_config()


async def a_get_proxies(token: str):
    servers = await ServerDB.get_servers()
    server_data = servers.get(token)

    if server_data:
        return cycle(server_data.proxies)
    else:
        return cycle([None])


async def run_check(user, proxy_dict: dict | None) -> str:
    try:
        result = await check_updates(user['user_id'], proxy_dict)
    except aiohttp.ClientConnectionError:
        res = 'MOODLE CONNECTION FAILED'
    except asyncio.exceptions.TimeoutError:
        traceback.print_exc()
        res = 'TIMEOUT MOODLE'
    else:
        if result == 1:
            res = 'Success'
        elif result == -1:
            res = 'Failed to check Token and Email'

    return res


async def main():
    dsn = f"postgresql://{DB_USER}:{DB_PASSWD}@{DB_HOST}:{DB_PORT}/{DB_DB}"
    await DB.connect(dsn)

    proxies = await a_get_proxies(token)
    if not IS_UPDATE_CONTENT:
        while 1:
            timeout = aiohttp.ClientTimeout(total=15)
            user = {}
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f'{MAIN_HOST}/api/get_user?token={token}', ssl=False) as response:
                        if response.status == 200:
                            proxy = next(proxies)
                            data = await response.json()
                            user = data['user']
                            os.environ["ATT_STATE"] = "1"
                            result = await run_check(user, proxy)
                            params = {
                                'user_id': user['user_id'],
                                'result': result,
                            }
                            async with session.post(f'{MAIN_HOST}/api/update_user?token={token}', data=params, ssl=False) as response:
                                Logger.info(f"{user['user_id']} - {response.status} - {proxy.get('ip') if proxy else None}")
                        else:
                            await asyncio.sleep(5)
            except aiohttp.ClientConnectionError as exc:
                Logger.error(f"Failed to connect to Pocket Moodle Server")
                await asyncio.sleep(10)
            except Exception as exc:
                params = {
                    'user_id': user.get('user_id'),
                    'result': 'Error',
                }
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(f'{MAIN_HOST}/api/update_user?token={token}', data=params, ssl=False) as response:
                        Logger.error(f"{user.get('user_id', None)} {str(exc)}", exc_info=True)
                await asyncio.sleep(5)
    else:
        while 1:
            await update_course_contents(next(proxies))
            await asyncio.sleep(60*60)

def run_server():
    def root(request):
        return web.Response(text='Ok')

    asyncio.set_event_loop(asyncio.new_event_loop())
    app = web.Application()
    app.add_routes([web.get('/', root)])
    web.run_app(app, handle_signals=False, port=8000)


if __name__ == "__main__":
    threading.Thread(target=run_server, args=(), daemon=True).start()
    asyncio.run(main())
