import os

import dotenv
from aiogram import Bot, types
from arsenic import browsers, services

from functions.functions import set_arsenic_log_level

dotenv.load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_DB = os.getenv('REDIS_DB')
REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASSWD = os.getenv('REDIS_PASSWD')

MAIN_HOST = os.getenv('MAIN_HOST')
token = os.getenv('token')

TOKEN = os.getenv('TOKEN')

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.MARKDOWN_V2)

service = None
browser = None

def set_services():
    global service
    global browser
    set_arsenic_log_level()
    service = services.Chromedriver(binary='/usr/bin/chromedriver')
    service.log_file = os.devnull
    browser = browsers.Chrome()
    browser.capabilities = {
        "goog:chromeOptions": {"args": ['--headless', '--disable-gpu', "--no-sandbox",
                                        "--disable-dev-shm-usage", "--disable-crash-reporter",
                                        "--log-level=3", "--disable-extensions",
                                        "--disable-in-process-stack-traces", "--disable-logging",
                                        "--output=/dev/null"]}}
set_services()