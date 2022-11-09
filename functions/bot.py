import asyncio

from aiogram import types
from aiogram.utils import exceptions
from config import bot
from functions.logger import logger


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
