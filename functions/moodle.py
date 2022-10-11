import asyncio
from curses.ascii import isdigit
import json
import os
from asyncio import sleep

import aiohttp
import dotenv
from arsenic import browsers, get_session, services
from arsenic.errors import UnknownArsenicError
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from webdriver_manager.chrome import ChromeDriverManager

from functions.functions import (decrypt, get_cookies_data,
                                 set_arsenic_log_level)
from functions.gpa import get_soup, login_and_get_gpa
from functions.moodle_functions import (add_new_courses, add_new_courses, auth_moodle, check_cookies,
                                        clear_courses, get_assignments_of_course, get_courses, get_grades_of_course)
from functions import aioredis
from functions.logger import logger

dotenv.load_dotenv()

TOKEN = os.getenv('TOKEN')

host = os.getenv('HOST')
port = os.getenv('PORT')
login = os.getenv('LOGIN')
passwd = os.getenv('PASSWD')

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.MARKDOWN_V2)
dp = Dispatcher(bot)


async def delete_user(chat_id):
    await aioredis.redis.delete(chat_id)


async def send(chat_id, text):
    markup = types.InlineKeyboardMarkup()
    switch_button = types.InlineKeyboardButton(text='Delete', callback_data="delete")
    markup.add(switch_button)
    try:
        await bot.send_message(chat_id, text, reply_markup=markup, disable_notification=True)
    except exceptions.BotBlocked:
        await delete_user(chat_id)
    except exceptions.ChatNotFound:
        await delete_user(chat_id)
    except exceptions.RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return await send(chat_id, text)
    except exceptions.UserDeactivated:
        await delete_user(chat_id)
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


async def set_grades(user, session, courses_names, courses_ids, active_courses_ids):
    new_grades = ['New grades:']
    updated_grades = ['Updated grades:']

    courses = clear_courses(user, courses_ids, active_courses_ids)
    add_new_courses(user, courses_names, courses_ids, courses)
    clear_courses(user, courses_ids, active_courses_ids)

    group = await asyncio.gather(*[get_grades_of_course(session, user, key) for key in user['courses']])
    
    if int(user['grades_sub']):
        index_new = 0
        index_updated = 0
        for item in group:
            if len(new_grades[index_new]) < 3500:
                new_grades[index_new] += item[0]
            else:
                index_new += 1
                new_grades.append(item[0])

            if len(updated_grades[index_updated]) < 3500:
                updated_grades[index_updated] += item[1]
            else:
                index_updated += 1
                updated_grades.append(item[1])

        if not int(user['ignore']) and await aioredis.is_active_sub(user['user_id']):
            for item in new_grades:
                if len(item) < 20:
                    continue
                await send(user['user_id'], item)
            for item in updated_grades:
                if len(item) < 20:
                    continue
                await send(user['user_id'], item)


async def set_deadlines(user, session, courses_names, courses_ids, active_courses_ids, proxy):
    updated_deadlines = ['Updated deadlines:']
    new_deadlines = ['New deadlines:']
    upcoming_deadlines = ['Upcoming deadlines:']
    
    courses = clear_courses(user, courses_ids, active_courses_ids)
    add_new_courses(user, courses_names, courses_ids, courses)
    clear_courses(user, courses_ids, active_courses_ids)

    group = await asyncio.gather(*[get_assignments_of_course(session, user, key, proxy) for key in user['courses']])
    
    if int(user['deadlines_sub']):
        index_updated = 0
        index_new = 0
        index_upcoming = 0
        for item in group:
            if len(updated_deadlines[index_updated]) < 3500:
                updated_deadlines[index_updated] += item[0]
            else:
                index_updated += 1
                updated_deadlines.append(item[0])
            if len(new_deadlines[index_new]) < 3500:
                new_deadlines[index_new] += item[1]
            else:
                index_new += 1
                new_deadlines.append(item[1])
            if len(upcoming_deadlines[index_upcoming]) < 3500:
                upcoming_deadlines[index_upcoming] += item[2]
            else:
                index_upcoming += 1
                upcoming_deadlines.append(item[2])
    
        if not int(user['ignore']) and await aioredis.is_active_sub(user['user_id']):
            for item in updated_deadlines:
                if len(item) < 20:
                    continue
                await send(user['user_id'], item)
            for item in new_deadlines:
                if len(item) < 20:
                    continue
                await send(user['user_id'], item)
            for item in upcoming_deadlines:
                if len(item) < 20:
                    continue
                await send(user['user_id'], item)


async def check_updates(user):
    user['passwd'] = decrypt(user['passwd'], user['barcode'])

    login_state = False
    cookies = json.loads(user.get('cookies', '{}'))
    msg = ''

    if cookies == {}:
        get_cookies_state = True
    else:
        get_cookies_state = await check_cookies(cookies)

    if get_cookies_state:
        if str(user['barcode']).isdigit():
            if int(user['barcode']) >= 210000:
                cookies, login_state, msg = await get_cookies(user['user_id'], user['barcode'], user['passwd'])
        else:    
            cookies, login_state, msg = await get_cookies(user['user_id'], user['barcode'], user['passwd'])
        if msg != '':
            return msg
    else:
        login_state = True

    try:
        connector = aiohttp.TCPConnector(limit_per_host=100)
        session_timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=30)
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', connector=connector, cookies=cookies, timeout=session_timeout) as session:
            if str(user['barcode']).isdigit():
                if int(user['barcode']) < 210000:
                    login_state = await auth_moodle(user, session)
            if login_state:
                
                courses_ids, courses_names, active_courses_ids = await get_courses(session)

                await set_grades(user, session, courses_names, courses_ids, active_courses_ids)
                
                proxy = f'http://{login}:{passwd}@{host}:{port}'
                await set_deadlines(user, session, courses_names, courses_ids, active_courses_ids, proxy)

                await aioredis.redis.hset(user['user_id'], 'courses', json.dumps(user['courses']))
                await aioredis.redis.hset(user['user_id'], 'cookies', json.dumps(cookies))
                await aioredis.redis.hset(user['user_id'], 'att_statistic', json.dumps(user['att_statistic']))
                await aioredis.redis.hset(user['user_id'], 'ignore', 0)
                return 1
            else:
                return 0
    except Exception as exc:
        await session.close()
        logger.error(exc, exc_info=True)
        return -1
