import json
import logging.config
from functools import wraps
from typing import Any, Callable, Mapping

from aiogram import types


class Logger(logging.Logger):
    _config_loaded = False
    _config = {}

    @classmethod
    def load_config(cls) -> None:
        if not cls._config_loaded:
            try:
                with open("logger_config.json", "r", encoding="UTF-8") as config_file:
                    cls._config = json.load(config_file)
                    cls._config_loaded = True
            except FileNotFoundError:
                cls._config = {}
            except json.JSONDecodeError:
                print("Error: Invalid JSON format in config file")
            logging.config.dictConfig(cls._config)
            cls.logger = logging.getLogger("custom")

    @classmethod
    def log_msg(cls, func) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            arg = args[0]
            if arg.__class__ is types.Message:
                msg: types.Message = arg
                if msg.chat.id == msg.from_user.id:
                    cls.info(f"{msg.from_user.id} - {msg.text}")
                else:
                    cls.info(f"{msg.from_user.id} / {msg.chat.id} - {msg.text}")

            elif arg.__class__ is types.CallbackQuery:
                callback: types.CallbackQuery = arg
                if callback.message.chat.id == callback.from_user.id:
                    cls.info(f"{callback.from_user.id} - {callback.data}")
                else:
                    cls.info(f"{callback.from_user.id} / {callback.message.chat.id} - {callback.data}")

            return func(*args, **kwargs)

        return wrapper

    @classmethod
    def error(  # pylint: disable=arguments-differ, arguments-renamed
        cls,
        msg: object,
        exc_info=None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        cls.logger.error(msg=msg, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)

    @classmethod
    def info(  # pylint: disable=arguments-differ, arguments-renamed
        cls,
        msg: object,
        exc_info=None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        cls.logger.info(msg=msg, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)
