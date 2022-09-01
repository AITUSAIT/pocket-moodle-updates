import json
import logging
from asyncio import sleep
import traceback

import structlog
from bs4 import BeautifulSoup

from functions import aioredis
from functions.logger import logger


async def get_cookies_data(session):
    cookies = {}
    session_cookies = await session.get_all_cookies()
    for cookie in session_cookies:
        cookies[cookie['name']] = cookie['value']
    return cookies


async def set_arsenic_log_level(level=logging.WARNING):
    logger = logging.getLogger('arsenic')

    def logger_factory():
        return logger

    structlog.configure(logger_factory=logger_factory)
    logger.setLevel(level)


async def get_soup(session):
    url = "https://login.microsoftonline.com/158f15f3-83e0-4906-824c-69bdc50d9d61/oauth2/v2.0/authorize?client_id=9f15860b-4243-4610-845e-428dc4ae43a8&response_type=code&redirect_uri=https%3A%2F%2Fdu.astanait.edu.kz%2Flogin&response_mode=query&scope=offline_access%20user.read%20mail.read&state=12345"
    await session.get(url)
    await sleep(5)
    await session.get('https://du.astanait.edu.kz/transcript')
    await sleep(5)
    soup = await session.get_page_source()
    return soup


async def get_total_gpa(soup):
    soup = BeautifulSoup(soup, 'html.parser')

    table = soup.find('table')
    text_avg_gpa = table.find('tfoot', {'class': 'ant-table-summary'}).text

    array_gpa = []
    rows = table.find_all('tr')
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) > 0:
            if 'trimester' in str(cells[1].text).lower():
                array_gpa.append(str(cells[1].text))
    array_gpa.append(text_avg_gpa)

    return array_gpa


async def login_and_get_gpa(user_id, soup):
    try:
        arr_gpa = await get_total_gpa(soup)

        gpa_text = "{"
        for item in arr_gpa:
            text, gpa = item.split(' - ')
            gpa_dict = f'"{text}": {gpa},'
            gpa_text += gpa_dict
        gpa_text = gpa_text[:-1] +"}"
        gpa_dict = json.loads(gpa_text)

        data = {}
        data['gpa'] = gpa_dict
            
        await aioredis.set_key(user_id, 'gpa', data['gpa'])
        return 1
    except Exception as exc:
        logger.error(user_id, exc_info=True)
        return -1