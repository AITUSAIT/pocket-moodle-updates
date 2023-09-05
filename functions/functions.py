import asyncio
from datetime import datetime, timedelta
import time


def clear_MD(text):
    text = str(text)
    symbols = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for sym in symbols:
        text = text.replace(sym, f"\{sym}")

    return text


def replace_grade_name(name: str):
    strings = ['Включая незаполненные оценки.', '(not to edit)', 'Include empty grades.']
    for string in strings:
        name = name.replace(string, '')
    return name


def get_diff_time(time_str):
    due = datetime.strptime(time_str, '%A, %d %B %Y, %I:%M %p')
    now = datetime.now()
    diff = due-now
    return chop_microseconds(diff)
    

def chop_microseconds(delta):
    return delta - timedelta(microseconds=delta.microseconds)


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
