from asyncio import sleep
import os

from arsenic import get_session
from arsenic.errors import UnknownArsenicError

from config import browser, service
from functions import aioredis
from functions.bot import send
from functions.functions import get_cookies_data
from functions.gpa import get_soup, login_and_get_gpa
from functions.logger import logger


async def get_cookies(user_id, BARCODE, PASSWD):
    try:
        async with get_session(service, browser) as session:
            url = "https://moodle.astanait.edu.kz/auth/oidc/"
            await session.get(url)
            try:
                count = 0
                while count < 100:
                    try:
                        count += 1
                        login = await session.get_element('input[name=loginfmt]')
                        button = await session.get_element('input[id=idSIButton9]')
                        await sleep(0.1)
                        if await button.is_displayed():
                            await login.send_keys(BARCODE+"@astanait.edu.kz")
                            await button.click()
                            break
                    except:
                        await sleep(0.1)

                await sleep(2)
                try:
                    error = await session.get_element('div[id=usernameError]')
                    if await error.is_displayed():
                        if not await aioredis.check_if_msg(user_id):
                            await send(user_id, 'Invalid login or password\n/register\_moodle to fix')
                        await session.close()
                        return {}, False, 'Invalid Login (barcode)'
                except:
                    pass

                count = 0
                while count < 100:
                    try:
                        count += 1
                        passwd = await session.get_element('input[name=passwd]')
                        button = await session.get_element('input[id=idSIButton9]')
                        await sleep(0.1)
                        if await button.is_displayed():
                            await passwd.send_keys(PASSWD)
                            await button.click()
                            break
                    except UnknownArsenicError as UAE:
                        await session.close()
                        return {}, False, -1
                    except:
                        await sleep(0.1)

                await sleep(2)
                try:
                    error = await session.get_element('div[id=passwordError]')
                    if await error.is_displayed():
                        if not await aioredis.check_if_msg(user_id):
                            await send(user_id, 'Invalid login or password\n/register\_moodle to fix')
                        await session.close()
                        return {}, False, 'Invalid Login (passwd)'
                except:
                    pass
                try:
                    error = await session.get_element('input[id=idSubmit_ProofUp_Redirect]')
                    if await error.is_displayed():
                        await session.close()
                        return {}, False, 'Invalid Login (proof)'
                except:
                    pass

                count = 0
                while count < 100:
                    try:
                        count += 1
                        button = await session.get_element('input[id=idSIButton9]')
                        await sleep(0.1)
                        if await button.is_displayed():
                            await button.click()
                            break
                    except:
                        await sleep(0.1)

                if count < 100:
                    cookies = await get_cookies_data(session)
                    await login_and_get_gpa(user_id, await get_soup(session))
                    await session.close()
                    return cookies, True, ''
                else:
                    await session.close()
                    return {}, False, -1
            except Exception as exc:
                logger.error(user_id, exc_info=True)
                await session.close()
                return {}, False, -1
    except BlockingIOError:
        await get_cookies(user_id, BARCODE, PASSWD)