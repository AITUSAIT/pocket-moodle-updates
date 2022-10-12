import asyncio
import os

import dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions

from functions.logger import logger

dotenv.load_dotenv()

TOKEN = os.getenv('TOKEN')

host = os.getenv('HOST')
port = os.getenv('PORT')
login = os.getenv('LOGIN')
passwd = os.getenv('PASSWD')

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
