import asyncio

from aiogram import types
from aiogram.utils import exceptions
from aiohttp import client_exceptions

from config import bot
from modules.logger import Logger


async def send(chat_id: int, text: str, register: bool=False):
    markup = types.InlineKeyboardMarkup()
    if not register:
        markup.add(types.InlineKeyboardButton(text='Delete', callback_data="delete"))
    else:
        markup.add(types.InlineKeyboardButton('Register account', callback_data=f'register'))

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
    except client_exceptions.ClientConnectionError:
        await asyncio.sleep(5)
        return await send(chat_id, text)
    except Exception:
        Logger.error(f"{chat_id}\n{text}\n", exc_info=True)

