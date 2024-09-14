import dotenv
from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode
from pytz import timezone

from modules.utils.config import get_from_env

dotenv.load_dotenv()

PM_HOST = str(get_from_env("PM_HOST"))
PM_TOKEN = str(get_from_env("PM_TOKEN"))

TOKEN = str(get_from_env("TG_TOKEN"))

IS_UPDATE_CONTENT = bool(int(get_from_env("IS_UPDATE_CONTENT")))

TZ_RAW = str(get_from_env("TZ", "Asia/Aqtobe"))
TZ = timezone(TZ_RAW) if TZ_RAW else timezone

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
