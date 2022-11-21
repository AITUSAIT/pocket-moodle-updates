import asyncio
from http.cookies import SimpleCookie

from functions import aioredis
from functions.bot import send
from moodle_module import Moodle, UserType


async def check_updates(user_id):
    user: UserType = await aioredis.get_user(user_id)

    if user.is_registered_moodle:
        moodle = Moodle(user)
        await moodle.check()

        if moodle.user.login_status and moodle.user.token:
            courses = await moodle.get_courses()
            active_courses_ids = await moodle.get_active_courses_ids()
            course_ids = list(course['id'] for course in courses)

            courses_ass = (await moodle.get_assignments())['courses']
            courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])

            await moodle.add_new_courses(courses, active_courses_ids)
            await asyncio.gather(*[moodle.get_attendance(course_id) for course_id in active_courses_ids])

            new_grades, updated_grades = await moodle.set_grades(courses_grades)
            updated_deadlines, new_deadlines, upcoming_deadlines = await moodle.set_assigns(courses_ass, active_courses_ids)

            if moodle.user.is_sub_grades and not moodle.user.is_ignore and moodle.user.is_active_sub:
                for items in [new_grades, updated_grades, updated_deadlines, new_deadlines, upcoming_deadlines]:
                    for item in items:
                        if len(item) < 20:
                            continue
                        await send(moodle.user.user_id, item)
            
            if moodle.user.is_ignore:
                await send(moodle.user.user_id, 'Your courses are *ready*\!')

            if moodle.user.cookies.__class__ is SimpleCookie:
                moodle.user.cookies = {k: v.value for k, v in moodle.user.cookies.items()}
            await aioredis.set_key(moodle.user.user_id, 'token', moodle.user.token)
            await aioredis.set_key(moodle.user.user_id, 'cookies', moodle.user.cookies)
            await aioredis.set_key(moodle.user.user_id, 'courses', moodle.user.courses)
            await aioredis.set_key(moodle.user.user_id, 'att_statistic', moodle.user.att_statistic)
            await aioredis.set_key(moodle.user.user_id, 'ignore', '0')
            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


