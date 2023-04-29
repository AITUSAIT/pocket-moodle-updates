import asyncio
import time
from http.cookies import SimpleCookie
import traceback

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWD, REDIS_PORT, REDIS_USER
from functions import aioredis
from functions.bot import send
from functions.functions import timeit
from main import a_get_proxies, get_proxies
from moodle_module import Moodle, UserType

logs = False


@timeit
async def check_updates(user_id, proxy_dict: dict):
    def custom_print(*args):
        if logs:
            print(*args)

    start = time.time()
    
    user: UserType = await aioredis.get_user(user_id)
    # user.token = ''
    custom_print('>>>', "get_user", time.time() - start, '\n')

    if user.is_registered_moodle:
        moodle = Moodle(user, proxy_dict)
        await moodle.check()
        custom_print('>>>', "moodle.check()", time.time() - start, '\n')

        if moodle.user.login_status and moodle.user.token:
            courses = await moodle.get_courses()
            active_courses_ids = await moodle.get_active_courses_ids(courses)
            course_ids = list(int(course['id']) for course in courses)
            custom_print('>>>', "get_active_courses_ids", time.time() - start, '\n')


            courses_ass = (await moodle.get_assignments())['courses']
            courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])
            custom_print('>>>', "get_assignments_and_grades", time.time() - start, '\n')


            await moodle.add_new_courses(courses, active_courses_ids)
            custom_print('>>>', "add_new_courses", time.time() - start, '\n')

            # updated_att = await asyncio.gather(*[moodle.get_attendance(courses_grades, course_id) for course_id in course_ids])
            # custom_print('>>>', "get_attendance", time.time() - start, '\n')

            new_grades, updated_grades = await moodle.set_grades(courses_grades)
            custom_print('>>>', "set_grades", time.time() - start, '\n')
            if moodle.user.is_active_sub:
                updated_deadlines, new_deadlines, upcoming_deadlines = await moodle.set_assigns(courses_ass, course_ids)
                custom_print('>>>', "set_assigns", time.time() - start, '\n')

            if moodle.user.is_active_sub:
                if moodle.user.token_du:
                    try:
                        await moodle.set_gpa(await moodle.get_gpa())
                    except:
                        ...
                    custom_print('>>>', "get_gpa", time.time() - start, '\n')

                    curriculum = await moodle.get_curriculum(1)
                    curriculum.extend(await moodle.get_curriculum(2))
                    curriculum.extend(await moodle.get_curriculum(3))
                    await moodle.set_curriculum(curriculum)
                    
                    custom_print('>>>', "get_curriculum", time.time() - start, '\n')
                    await aioredis.set_key(moodle.user.user_id, 'curriculum', moodle.user.curriculum)
                    if moodle.user.gpa:
                        await aioredis.set_key(moodle.user.user_id, 'gpa', moodle.user.gpa)

            if moodle.user.is_active_sub:
                if moodle.user.is_ignore in [0, 2]:
                    for items in [new_grades, updated_grades, updated_deadlines, new_deadlines, upcoming_deadlines]:
                        for item in items:
                            if len(item) > 20:
                                await send(moodle.user.user_id, item)
                    if moodle.user.is_ignore == 2:
                        await send(moodle.user.user_id, 'Updated\!')
                else:
                    await send(moodle.user.user_id, 'Your courses are *ready*\!')
            else:
                if moodle.user.is_ignore == 2:
                    await send(moodle.user.user_id, 'Updated\!')
                elif moodle.user.is_ignore == 1:
                    await send(moodle.user.user_id, 'Your courses are *ready*\!')

            custom_print('>>>', "send_msg", time.time() - start, '\n')

            if moodle.user.cookies.__class__ is SimpleCookie:
                moodle.user.cookies = {k: v.value for k, v in moodle.user.cookies.items()}

            await aioredis.set_key(moodle.user.user_id, 'email', moodle.user.email)
            await aioredis.set_key(moodle.user.user_id, 'token', moodle.user.token)
            await aioredis.set_key(moodle.user.user_id, 'cookies', moodle.user.cookies)
            await aioredis.set_key(moodle.user.user_id, 'courses', moodle.user.courses)
            await aioredis.set_key(moodle.user.user_id, 'ignore', '0')
            custom_print('>>>', "redis set_keys", time.time() - start, '\n')

            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


async def main():
    await aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    )
    proxies = await a_get_proxies()
    while 1:
        try:
            await check_updates('626591599', next(proxies))
        except asyncio.exceptions.TimeoutError:
            print('Timeout MOODLE')
        except Exception as exc:
            print('ERROR')
            traceback.format_exc(exc)

asyncio.run(main())