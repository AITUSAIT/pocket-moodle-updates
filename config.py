import os

import dotenv
from aiogram import Bot, types

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
