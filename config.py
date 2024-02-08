import os

import dotenv
from aiogram import Bot, types

dotenv.load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DB = os.getenv("DB_DB")
DB_USER = os.getenv("DB_USER")
DB_PASSWD = os.getenv("DB_PASSWD")

MAIN_HOST = os.getenv("MAIN_HOST")
SERVER_TOKEN = os.getenv("token")

TOKEN = os.getenv("TOKEN_bot")

IS_PROXY = bool(int(os.getenv("IS_PROXY")))
IS_UPDATE_CONTENT = bool(int(os.getenv("IS_UPDATE_CONTENT")))


bot = Bot(token=TOKEN, parse_mode=types.ParseMode.MARKDOWN_V2)


chrome_options = [
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-crash-reporter",
    "--log-level=3",
    "--disable-extensions",
    "--disable-in-process-stack-traces",
    "--disable-logging",
    "--output=/dev/null",
    "--disable-features=Translate",
    "--force-device-scale-factor=1",
]
