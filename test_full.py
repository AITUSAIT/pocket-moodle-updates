import asyncio
from http.cookies import SimpleCookie
import time

from config import (MAIN_HOST, REDIS_DB, REDIS_HOST, REDIS_PASSWD, REDIS_PORT,
                    REDIS_USER, token)
from functions import aioredis
from functions.bot import send
from functions.functions import timeit
from moodle_module import Moodle, UserType


@timeit
async def check_updates(user_id):
    start = time.time()
    
    await aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    )
    user: UserType = await aioredis.get_user(user_id)
    print('>>>', "get_user", time.time() - start, '\n')

    if user.is_registered_moodle:
        moodle = Moodle(user)
        await moodle.check()
        print('>>>', "moodle.check()", time.time() - start, '\n')

        if moodle.user.login_status and moodle.user.token:
            courses = await moodle.get_courses()
            active_courses_ids = await moodle.get_active_courses_ids()
            course_ids = list(course['id'] for course in courses)
            print('>>>', "get_active_courses_ids", time.time() - start, '\n')


            courses_ass = (await moodle.get_assignments())['courses']
            courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])
            print('>>>', "get_assignments_and_grades", time.time() - start, '\n')


            await moodle.add_new_courses(courses, active_courses_ids)
            print('>>>', "add_new_courses", time.time() - start, '\n')
            await asyncio.gather(*[moodle.get_attendance(courses_grades, course_id) for course_id in active_courses_ids])
            print('>>>', "get_attendance", time.time() - start, '\n')

            new_grades, updated_grades = await moodle.set_grades(courses_grades)
            updated_deadlines, new_deadlines, upcoming_deadlines = await moodle.set_assigns(courses_ass, active_courses_ids)
            print('>>>', "set_grades_and_assigns", time.time() - start, '\n')

            calendar = await moodle.get_calendar()
            print('>>>', "get_calendar", time.time() - start, '\n')

            if moodle.user.token_du:
                await moodle.set_gpa(await moodle.get_gpa())
                print('>>>', "get_gpa", time.time() - start, '\n')

                curriculum = await moodle.get_curriculum(1)
                curriculum.extend(await moodle.get_curriculum(2))
                curriculum.extend(await moodle.get_curriculum(3))
                await moodle.set_curriculum(curriculum)
                
                print('>>>', "get_curriculum", time.time() - start, '\n')
                await aioredis.set_key(moodle.user.user_id, 'curriculum', moodle.user.curriculum)
                await aioredis.set_key(moodle.user.user_id, 'gpa', moodle.user.gpa)


            if moodle.user.is_sub_grades and not moodle.user.is_ignore and moodle.user.is_active_sub:
                for items in [new_grades, updated_grades, updated_deadlines, new_deadlines, upcoming_deadlines]:
                    for item in items:
                        if len(item) < 20:
                            continue
                        await send(moodle.user.user_id, item)
            print('>>>', "send_msg", time.time() - start, '\n')
            
            if moodle.user.is_ignore:
                await send(moodle.user.user_id, 'Your courses are *ready*\!')

            if moodle.user.cookies.__class__ is SimpleCookie:
                moodle.user.cookies = {k: v.value for k, v in moodle.user.cookies.items()}

            await aioredis.set_key(moodle.user.user_id, 'token', moodle.user.token)
            await aioredis.set_key(moodle.user.user_id, 'cookies', moodle.user.cookies)
            await aioredis.set_key(moodle.user.user_id, 'courses', moodle.user.courses)
            await aioredis.set_key(moodle.user.user_id, 'att_statistic', moodle.user.att_statistic)
            await aioredis.set_key(moodle.user.user_id, 'calendar', calendar)
            await aioredis.set_key(moodle.user.user_id, 'ignore', '0')
            print('>>>', "redis set_keys", time.time() - start, '\n')

            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


asyncio.run(check_updates(626591599))