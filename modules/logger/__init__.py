import logging
import logging.config
from typing import Mapping


class Logger(logging.Logger):
    @classmethod
    def load_config(cls):
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "custom": {
                    "format": "{asctime} - {levelname} - {message}",
                    "style": "{",
                    "datefmt": "%d/%m %H:%M:%S",
                    "encoding": "UTF-8"
                }
            },
            "handlers": {
                "stdout": {
                    "level": "INFO",
                    "class": "logging.StreamHandler",
                    "formatter": "custom"
                },
                "file": {
                    "level": "INFO",
                    "class": "logging.FileHandler",
                    "filename": "logs.log",
                    "formatter": "custom",
                    # "mode": "a"
                },
                "file_debug": {
                    "level": "DEBUG",
                    "class": "logging.FileHandler",
                    "filename": "logs_debug.log",
                    "formatter": "custom",
                    # "mode": "a"
                }
            },
            "loggers": {
                "custom_std": {
                    "handlers": ["stdout"],
                    "level": "INFO",
                    "propagate": True
                },
                "file": {
                    "handlers": ["file", "stdout"],
                    "level": "INFO",
                    "propagate": True
                },
                "file_debug": {
                    "handlers": ["file_debug"],
                    "level": "DEBUG",
                    "propagate": True
                }
            }
        }

        logging.config.dictConfig(config)
        cls.logger = logging.getLogger('file')

    @classmethod
    def error(cls, msg: object,
              exc_info = None,
              stack_info: bool = False,
              stacklevel: int = 1,
              extra: Mapping[str, object] | None = None):
        cls.logger.error(msg=msg,
                         exc_info=exc_info,
                         stack_info=stack_info,
                         stacklevel=stacklevel,
                         extra=extra)
        
    @classmethod
    def info(cls, msg: object,
              exc_info = None,
              stack_info: bool = False,
              stacklevel: int = 1,
              extra: Mapping[str, object] | None = None):
        cls.logger.info(msg=msg,
                         exc_info=exc_info,
                         stack_info=stack_info,
                         stacklevel=stacklevel,
                         extra=extra)
