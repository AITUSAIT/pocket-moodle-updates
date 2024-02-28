import asyncio
from itertools import cycle

from functions.bot import send
from modules.database import CourseDB, DeadlineDB, GradeDB, NotificationDB, SettingsBotDB, UserDB
from modules.moodle import Moodle, User

count_student = cycle([0, 1, 2])


async def check_updates(user_id) -> int | str:
    _ = await UserDB.get_user(user_id)
    user: User = User(
        user_id=_.user_id,
        api_token=_.api_token,
        register_date=_.register_date,
        mail=_.mail,
        last_active=_.last_active,
        id=None,
        courses=(await CourseDB.get_courses(user_id)),
        msg=None,
    )
    settings = await SettingsBotDB.get_settings(user_id)
    notifications = await NotificationDB.get_notification_status(user.user_id)

    moodle = Moodle(user, notifications)
    if not await moodle.check():
        return -1

    courses = await moodle.get_courses()
    active_courses_ids = await moodle.get_active_courses_ids(courses)
    course_ids = list(int(course["id"]) for course in courses)

    courses_ass = (await moodle.get_assignments())["courses"]
    if not (notifications.is_update_requested or notifications.is_newbie_requested):
        course_ids = active_courses_ids
    courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])

    await moodle.add_new_courses(courses, active_courses_ids)
    user.courses = await CourseDB.get_courses(user_id)

    await moodle.set_grades(courses_grades, course_ids)
    if not settings.status or not settings.notification_grade:
        moodle.new_grades, moodle.updated_grades = [], []

    if (
        moodle.user.is_active_sub()
        or next(count_student) == 0
        or notifications.is_update_requested
        or notifications.is_newbie_requested
    ):
        await moodle.set_assigns(courses_ass)
        if not settings.status or not settings.notification_deadline:
            moodle.updated_deadlines, moodle.new_deadlines, moodle.upcoming_deadlines = [], [], []

    await DeadlineDB.commit()
    await GradeDB.commit()

    if moodle.user.is_active_sub() and not notifications.is_newbie_requested:
        for items in [
            moodle.new_grades,
            moodle.updated_grades,
            moodle.updated_deadlines,
            moodle.new_deadlines,
            moodle.upcoming_deadlines,
        ]:
            for item in items:
                if len(item) > 20:
                    await send(moodle.user.user_id, item)

    if notifications.is_update_requested:
        await send(moodle.user.user_id, "Updated\!")
        await NotificationDB.set_notification_status(user.user_id, "is_update_requested", False)
    elif notifications.is_newbie_requested:
        await send(moodle.user.user_id, "Your courses are *ready*\!")
        await NotificationDB.set_notification_status(user.user_id, "is_newbie_requested", False)

    del user
    del moodle
    return 1
