import asyncio
import logging
import sys
import traceback

import aiohttp

from functions.moodle import check_updates
from modules.pm_api.api import PocketMoodleAPI
from modules.pm_api.models import User


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S",
    stream=sys.stdout
)


async def run_update_check(user: User) -> str:
    """Check for updates for a specific user."""
    try:
        return await check_updates(user.user_id)
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


async def main():
    """Main loop for continuously checking and updating user status."""
    while True:
        try:
            user = await PocketMoodleAPI().get_user_from_queue()
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            logging.error("Failed to connect to Moodle Server")
            await asyncio.sleep(10)

        try:
            await process_user_update(user)
        except Exception as exc:
            logging.error(f"Error processing user {user.user_id}: {str(exc)}", exc_info=True)
            await asyncio.sleep(5)


asyncio.run(main())
