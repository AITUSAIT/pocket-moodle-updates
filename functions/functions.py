import asyncio
import logging
import time
import structlog


def clear_MD(text):
    text = str(text)
    symbols = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for sym in symbols:
        text = text.replace(sym, f"\{sym}")

    return text
    

def timeit(func):
    async def process(func, *args, **params):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **params)
        else:
            return func(*args, **params)

    async def helper(*args, **params):
        start = time.time()
        result = await process(func, *args, **params)

        # Test normal function route...
        # result = await process(lambda *a, **p: print(*a, **p), *args, **params)

        print('>>>', func.__name__, time.time() - start, '\n')
        return result

    return helper


async def set_arsenic_log_level(level = logging.WARNING):
    logger = logging.getLogger('arsenic')


    def logger_factory():
        return logger

    structlog.configure(logger_factory=logger_factory)
    logger.setLevel(level)


async def get_cookies_data(session):
    cookies = {}
    session_cookies = await session.get_all_cookies()
    for cookie in session_cookies:
        cookies[cookie['name']] = cookie['value']
    return cookies


def crypto(message: str, secret: str) -> str:
    new_chars = list()
    i = 0

    for num_chr in (ord(c) for c in message):
        num_chr ^= ord(secret[i])
        new_chars.append(num_chr)

        i += 1
        if i >= len(secret):
            i = 0

    return ''.join(chr(c) for c in new_chars)


def encrypt_xor(message: str, secret: str) -> str:
    return crypto(message, secret).encode('utf-8').hex()


def decrypt(message_hex: str, secret: str) -> str:
    message = bytes.fromhex(message_hex).decode('utf-8')
    return crypto(message, secret)