import asyncio
import logging
import sys
import traceback
from time import time

import aiohttp

from functions.moodle import check_updates
from modules.pm_api.api import PocketMoodleAPI
from modules.pm_api.models import User

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%d/%b/%Y %H:%M:%S", stream=sys.stdout
)


async def run_update_check(user: User) -> str:
    """Check for updates for a specific user."""
    try:
        start = time()
        result = await check_updates(user)
        end = time()
        logging.info(f"{end-start} sec")
        return result
    except aiohttp.ClientConnectionError:
        return "MOODLE CONNECTION FAILED"
    except asyncio.TimeoutError:
        traceback.print_exc()
        return "TIMEOUT MOODLE"
    except Exception:
        traceback.print_exc()
        return "Unexpected Error"


async def process_user_update(user: User):
    """Process update for a single user and send the result to the server."""
    result = await run_update_check(user)

    await PocketMoodleAPI().log_queue_result(user_id=user.user_id, log=result)
    logging.info(f"{user.user_id} - {result}")


async def test():
    user = await PocketMoodleAPI().get_user(626591599)
    if not user:
        logging.error("User not found!")
        return
    await process_user_update(user)


asyncio.run(test())
