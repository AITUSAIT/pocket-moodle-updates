import asyncio
from http.cookies import SimpleCookie
from itertools import cycle

from functions import aioredis
from functions.bot import send
from moodle_module import Moodle, UserType


count_student = cycle([0, 1, 2])


async def check_updates(user_id, proxy_dict: dict) -> int | str:
    user: UserType = await aioredis.get_user(user_id)

    if user.is_registered_moodle:
        moodle = Moodle(user, proxy_dict)
        await moodle.check()

        if moodle.user.login_status and moodle.user.token:
            courses = await moodle.get_courses()
            active_courses_ids = await moodle.get_active_courses_ids(courses)
            course_ids = list(course['id'] for course in courses)

            if moodle.user.is_active_sub:
                courses_ass = (await moodle.get_assignments())['courses']
            courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])

            await moodle.add_new_courses(courses, active_courses_ids)
            
            # updated_att = await asyncio.gather(*[moodle.get_attendance(courses_grades, course_id) for course_id in active_courses_ids])
            # if not user.att_notify:
            #     updated_att = []

            new_grades, updated_grades = await moodle.set_grades(courses_grades)
            if moodle.user.is_active_sub or next(count_student) == 0:
                updated_deadlines, new_deadlines, upcoming_deadlines = await moodle.set_assigns(courses_ass, active_courses_ids)

            if moodle.user.is_active_sub:
                if moodle.user.token_du:
                    try:
                        await moodle.set_gpa(await moodle.get_gpa())
                    except:
                        ...

                    curriculum = await moodle.get_curriculum(1)
                    curriculum.extend(await moodle.get_curriculum(2))
                    curriculum.extend(await moodle.get_curriculum(3))
                    await moodle.set_curriculum(curriculum)

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
                elif moodle.user.is_ignore == 1:
                    await send(moodle.user.user_id, 'Your courses are *ready*\!')
            else:
                if moodle.user.is_ignore == 2:
                    await send(moodle.user.user_id, 'Updated\!')
                elif moodle.user.is_ignore == 1:
                    await send(moodle.user.user_id, 'Your courses are *ready*\!')

            if moodle.user.cookies.__class__ is SimpleCookie:
                moodle.user.cookies = {k: v.value for k, v in moodle.user.cookies.items()}

            await aioredis.set_key(moodle.user.user_id, 'email', moodle.user.email)
            await aioredis.set_key(moodle.user.user_id, 'token', moodle.user.token)
            await aioredis.set_key(moodle.user.user_id, 'cookies', moodle.user.cookies)
            await aioredis.set_key(moodle.user.user_id, 'courses', moodle.user.courses)
            # await aioredis.set_key(moodle.user.user_id, 'att_statistic', moodle.user.att_statistic)
            await aioredis.set_key(moodle.user.user_id, 'ignore', '0')
            del user
            del moodle
            return 1
        else:
            msg = user.msg
            del user
            del moodle
            return msg


