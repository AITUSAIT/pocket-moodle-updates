import asyncio
import json
import os
from asyncio import sleep

import aiohttp
import dotenv
from arsenic import browsers, get_session, services
from arsenic.errors import UnknownArsenicError
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions

from functions.functions import (decrypt, get_cookies_data,
                                 set_arsenic_log_level, timeit)
from functions.gpa import get_soup, login_and_get_gpa
from functions.moodle_functions import (add_new_courses, add_new_courses, auth_moodle,
                                        clear_courses, get_assignments_of_course, get_courses, get_grades_of_course)
from functions import aioredis
from functions.logger import logger

dotenv.load_dotenv()

TOKEN = os.getenv('TOKEN')

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.MARKDOWN_V2)
dp = Dispatcher(bot)


async def send(chat_id, text):
    markup = types.InlineKeyboardMarkup()
    switch_button = types.InlineKeyboardButton(text='Delete', callback_data="delete")
    markup.add(switch_button)
    try:
        await bot.send_message(chat_id, text, reply_markup=markup, disable_notification=True)
    except exceptions.BotBlocked:
        ...
    except exceptions.ChatNotFound:
        ...
    except exceptions.RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return await send(chat_id, text)
    except exceptions.UserDeactivated:
        ...
    except exceptions.TelegramAPIError:
        logger.error(f"{chat_id}\n{text}\n", exc_info=True)



async def get_cookies(user_id, BARCODE, PASSWD):
    await set_arsenic_log_level()
    import os
    service = services.Chromedriver(binary='/usr/bin/chromedriver')
    service.log_file = os.devnull
    browser = browsers.Chrome()
    browser.capabilities = {
        "goog:chromeOptions": {"args": ['--headless', '--disable-gpu', "--no-sandbox",
                                        "--disable-dev-shm-usage", "--disable-crash-reporter",
                                        "--log-level=3", "--disable-extensions",
                                        "--disable-in-process-stack-traces", "--disable-logging",
                                        "--output=/dev/null"]}}
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
                    return {}, False, -1
                except:
                    await sleep(0.1)

            await sleep(2)
            try:
                error = await session.get_element('div[id=passwordError]')
                if await error.is_displayed():
                    if not await aioredis.check_if_msg(user_id):
                        await send(user_id, 'Invalid login or password\n/register\_moodle to fix')
                    return {}, False, 'Invalid Login (passwd)'
            except:
                pass
            try:
                error = await session.get_element('input[id=idSubmit_ProofUp_Redirect]')
                if await error.is_displayed():
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
                return cookies, True, ''
            else:
                return {}, False, -1
        except Exception as exc:
            logger.error(user_id, exc_info=True)
            return {}, False, -1
