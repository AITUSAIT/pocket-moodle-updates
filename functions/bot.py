import asyncio

from aiogram import types
from aiogram.utils import exceptions

from config import bot
from functions import aioredis
from functions.logger import logger


async def send(chat_id, text):
    markup = types.InlineKeyboardMarkup()
    switch_button = types.InlineKeyboardButton(text='Delete', callback_data="delete")
    markup.add(switch_button)
    try:
        await bot.send_message(chat_id, text, reply_markup=markup, disable_notification=True)
    except exceptions.BotBlocked:
        await aioredis.set_sleep(chat_id)
        ...
    except exceptions.ChatNotFound:
        await aioredis.set_sleep(chat_id)
        ...
    except exceptions.RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return await send(chat_id, text)
    except exceptions.UserDeactivated:
        await aioredis.set_sleep(chat_id)
        ...
    except Exception:
        logger.error(f"{chat_id}\n{text}\n", exc_info=True)

