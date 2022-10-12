from datetime import datetime
import json

import aioredis
from functions.functions import decrypt

redis : aioredis.Redis = None


async def start_redis(user, passwd, host, port, db):
    global redis
    redis = await aioredis.from_url(f"redis://{user}:{passwd}@{host}:{port}/{db}", decode_responses=True)


async def set_key(key, key2, value):
    global redis
    if value.__class__ is dict:
        value = json.dumps(value)
    await redis.hset(key, key2, value)


async def get_key(dict_key, key):
    global redis
    return await redis.hget(dict_key, key)


async def set_keys(key, dict):
    global redis
    await redis.hmset(key, dict)


async def get_keys(dict_key, *keys):
    global redis
    return await redis.hmget(dict_key, *keys)


async def get_dict(key):
    global redis
    return await redis.hgetall(key)


async def get_user(user_id):
    data = await get_dict(user_id)
    user = type('', (), {})()

    user.user_id = data['user_id']
    user.id = None

    user.barcode = data.get('barcode', None)
    user.passwd = data.get('passwd', None)

    user.cookies = json.loads(data.get('cookies', '{}'))
    user.token = data.get('token', None)
    user.token_att = data.get('token_att', None)

    user.courses = json.loads(data.get('courses', '{}'))
    user.gpa = json.loads(data.get('gpa', '{}'))
    user.att_statistic = json.loads(data.get('att_statistic', '{}'))

    user.is_sub_grades = bool(int(data.get('grades_sub', 0)))
    user.is_sub_deadlines = bool(int(data.get('deadlines_sub', 0)))
    user.is_registered_moodle = await is_registered_moodle(user_id)
    user.is_active_sub = await is_active_sub(user_id)

    user.is_ignore = bool(int(data.get('ignore', 0)))

    if user.is_registered_moodle:
        user.passwd = decrypt(user.passwd, user.barcode)

    return user


async def if_user(user_id):
    global redis
    if await redis.hexists(user_id, 'user_id') == 0:
        return False
    else:
        return True


async def is_active_sub(user_id):
    if not await if_user(user_id):
        return False

    date_str = await get_key(user_id, 'end_date')

    if date_str is None:
        return False

    if datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f') > datetime.now():
        return True
    else:
        return False


async def is_activaited_demo(user_id):
    global redis
    if int(await redis.hget(user_id, 'demo')) == 1:
        return True
    else:
        return False


async def is_registered_moodle(user_id):
    global redis
    if await redis.hget(user_id, 'barcode'):
        return True
    else:
        return False


async def check_if_msg(user_id):
    if not await redis.hexists(user_id, 'message'):
        await redis.hset(user_id, 'message', 1)
        return False

    message = int(await redis.hget(user_id, 'message'))
    await redis.hset(user_id, 'message', 1)
    return message
    

async def close():
    await redis.close()
