import asyncio
from itertools import cycle

from functions.bot import send
from modules.database import (CourseDB, DeadlineDB, GradeDB, NotificationDB,
                              UserDB)
from modules.moodle import Moodle, User

count_student = cycle([0, 1, 2])


async def check_updates(user_id, proxy_dict: dict) -> int | str:
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

    moodle = Moodle(user, proxy_dict)
    if not await moodle.check():
        return -1 
    
    courses = await moodle.get_courses()
    active_courses_ids = await moodle.get_active_courses_ids(courses)
    course_ids = list(course['id'] for course in courses)

    courses_ass = (await moodle.get_assignments())['courses']
    courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])

    await moodle.add_new_courses(courses, active_courses_ids)
    CourseDB.get_courses.cache_clear()
    user.courses = await CourseDB.get_courses(user_id)

    new_grades, updated_grades = await moodle.set_grades(courses_grades)
    if moodle.user.is_active_sub() \
        or next(count_student) == 0 \
            or notification_status.is_update_requested \
                or notification_status.is_newbie_requested:
        updated_deadlines, new_deadlines, upcoming_deadlines = await moodle.set_assigns(courses_ass)
    await GradeDB.commit()
    await DeadlineDB.commit()

    if moodle.user.is_active_sub() and not notification_status.is_newbie_requested:
        for items in [new_grades, updated_grades, updated_deadlines, new_deadlines, upcoming_deadlines]:
            for item in items:
                if len(item) > 20:
                    await send(moodle.user.user_id, item)
    
    if notification_status.is_update_requested:
        await send(moodle.user.user_id, 'Updated\!')
        await NotificationDB.set_notification_status(user.user_id, 'is_update_requested', False)
    elif notification_status.is_newbie_requested:
        await send(moodle.user.user_id, 'Your courses are *ready*\!')
        await NotificationDB.set_notification_status(user.user_id, 'is_newbie_requested', False)

    del user
    del moodle
    return 1
