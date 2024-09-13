import os

import dotenv
from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode
from pytz import timezone

dotenv.load_dotenv()

MAIN_HOST = os.getenv("MAIN_HOST")
SERVER_TOKEN = os.getenv("token")

TOKEN = os.getenv("TOKEN_bot")

IS_UPDATE_CONTENT = bool(int(os.getenv("IS_UPDATE_CONTENT")))

TZ_RAW = os.getenv("TZ", "Asia/Aqtobe")
TZ = timezone(TZ_RAW) if TZ_RAW else timezone

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
