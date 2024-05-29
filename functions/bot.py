import asyncio

from aiogram import types
from aiogram.exceptions import TelegramNetworkError, TelegramNotFound, TelegramRetryAfter
from aiohttp.client_exceptions import ClientConnectionError

from config import bot
from modules.logger import Logger


async def send(chat_id: int, text: str, register: bool = False):
    buttons = [[]]
    if not register:
        buttons[0].append(types.InlineKeyboardButton(text="Delete", callback_data="delete"))
    else:
        buttons[0].append(types.InlineKeyboardButton(text="Register account", callback_data="register"))

    markup = types.InlineKeyboardMarkup(inline_keyboard=[[]])

    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, disable_notification=True)
    except TelegramNotFound:
        ...
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        return await send(chat_id, text)
    except (TelegramNetworkError, ClientConnectionError):
        await asyncio.sleep(5)
        return await send(chat_id, text)
    except Exception:
        Logger.error(f"{chat_id}\n{text}\n", exc_info=True)
