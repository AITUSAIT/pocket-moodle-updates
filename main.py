import asyncio
import traceback

import aiohttp

from config import DB_DB, DB_HOST, DB_PASSWD, DB_PORT, DB_USER, IS_UPDATE_CONTENT, MAIN_HOST, SERVER_TOKEN
from functions.moodle import check_updates
from functions.moodle_contents import MoodleContents
from modules.database import DB
from modules.logger import Logger

Logger.load_config()


async def run_update_check(user) -> str:
    """Check for updates for a specific user."""
    try:
        return await check_updates(user["user_id"])
    except aiohttp.ClientConnectionError:
        return "MOODLE CONNECTION FAILED"
    except asyncio.TimeoutError:
        traceback.print_exc()
        return "TIMEOUT MOODLE"
    except Exception:
        traceback.print_exc()
        return "Unexpected Error"


async def process_user_update(session, user, params):
    """Process update for a single user and send the result to the server."""
    result = await run_update_check(user)

    update_data = {
        "user_id": user["user_id"],
        "result": result,
    }

    async with session.post(f"{MAIN_HOST}/api/update_user", params=params, data=update_data, ssl=False) as response:
        Logger.info(f"User {user['user_id']} - Update status: {response.status}")


async def fetch_and_update_user(session, params):
    """Fetch user data from the server and update their Moodle status."""
    async with session.get(f"{MAIN_HOST}/api/get_user", params=params, ssl=False) as response:
        if response.status == 200:
            data = await response.json()
            return data["user"]

        Logger.error(await response.json())
        return None


async def main():
    """Main loop for continuously checking and updating user status."""
    dsn = f"postgresql://{DB_USER}:{DB_PASSWD}@{DB_HOST}:{DB_PORT}/{DB_DB}"
    await DB.connect(dsn)

    params = {"token": SERVER_TOKEN}
    timeout = aiohttp.ClientTimeout(total=15)

    if not IS_UPDATE_CONTENT:
        while True:
            user = {}
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    user = await fetch_and_update_user(session, params)
                    if user:
                        await process_user_update(session, user, params)
                    await asyncio.sleep(5)
            except aiohttp.ClientConnectionError:
                Logger.error("Failed to connect to Moodle Server")
                await asyncio.sleep(10)
            except Exception as exc:
                Logger.error(f"Error processing user {user.get('user_id')}: {str(exc)}", exc_info=True)
                await asyncio.sleep(5)
    else:
        while True:
            moodle_contents = MoodleContents()
            await moodle_contents.update_course_contents()
            await asyncio.sleep(60 * 60)


asyncio.run(main())
