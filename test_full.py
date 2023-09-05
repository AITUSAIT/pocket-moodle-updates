import asyncio
import time
import traceback
from itertools import cycle

from config import DB_DB, DB_HOST, DB_PASSWD, DB_PORT, DB_USER, token
from functions.bot import send
from main import a_get_proxies
from modules.database import (DB, CourseDB, DeadlineDB, GradeDB,
                              NotificationDB, UserDB)
from modules.moodle import Moodle, User

logs = True

count_student = cycle([0, 1, 2])


async def check_updates(user_id, proxy_dict: dict):
    def custom_print(*args):
        if logs:
            print(*args)

    start = time.time()
    
    _ = await UserDB.get_user(user_id)
    user: User = User(
        user_id=_.user_id,
        api_token=_.api_token,
        register_date=_.register_date,
        sub_end_date=_.sub_end_date,
        mail=_.mail, 
        id=None, 
        courses=(await CourseDB.get_courses(user_id)), 
        msg=None
    )
    notification_status = await NotificationDB.get_notification_status(user.user_id)
    custom_print('>>>', "get_user", time.time() - start, '\n')

    moodle = Moodle(user, proxy_dict)
    if not await moodle.check():
        return -1 
    
    courses = await moodle.get_courses()
    active_courses_ids = await moodle.get_active_courses_ids(courses)
    course_ids = list(course['id'] for course in courses)
    custom_print('>>>', "get_courses", time.time() - start, '\n')

    courses_ass = (await moodle.get_assignments())['courses']
    custom_print('>>>', "get_courses_ass", time.time() - start, '\n')
    courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in active_courses_ids])
    custom_print('>>>', "get_courses_grades", time.time() - start, '\n')

    await moodle.add_new_courses(courses, active_courses_ids)
    CourseDB.get_courses.cache_clear()
    user.courses = await CourseDB.get_courses(user_id)
    custom_print('>>>', "update_courses", time.time() - start, '\n')

    new_grades, updated_grades = await moodle.set_grades(courses_grades)
    custom_print('>>>', "set_grades", time.time() - start, '\n')

    if moodle.user.is_active_sub() \
        or next(count_student) == 0 \
            or notification_status.is_update_requested \
                or notification_status.is_newbie_requested:
        updated_deadlines, new_deadlines, upcoming_deadlines = await moodle.set_assigns(courses_ass)
    custom_print('>>>', "set_deadlines", time.time() - start, '\n')
    await DeadlineDB.commit()
    await GradeDB.commit()
    custom_print('>>>', "commit_grades_deadlines", time.time() - start, '\n')
    
    if moodle.user.is_active_sub() and not notification_status.is_newbie_requested:
        for items in [new_grades, updated_grades, updated_deadlines, new_deadlines, upcoming_deadlines]:
            for item in items:
                if len(item) > 20:
                    await send(moodle.user.user_id, item)
    custom_print('>>>', "send_messages", time.time() - start, '\n')
    
    if notification_status.is_update_requested:
        await send(moodle.user.user_id, 'Updated\!')
        await NotificationDB.set_notification_status(user.user_id, 'is_update_requested', False)
    elif notification_status.is_newbie_requested:
        await send(moodle.user.user_id, 'Your courses are *ready*\!')
        await NotificationDB.set_notification_status(user.user_id, 'is_newbie_requested', False)
    custom_print('>>>', "update_notifications", time.time() - start, '\n')

    del user
    del moodle
    return 1


async def main():
    dsn = f"postgresql://{DB_USER}:{DB_PASSWD}@{DB_HOST}:{DB_PORT}/{DB_DB}"
    await DB.connect(dsn)
    proxies = await a_get_proxies(token)
    try:
        await check_updates(626591599, next(proxies))
    except asyncio.exceptions.TimeoutError:
        print('Timeout MOODLE')
    except Exception as exc:
        print('ERROR')
        traceback.format_exc(exc)

asyncio.run(main())