import asyncio

from line_profiler import profile

from functions.bot import send
from modules.moodle import ExtendedUser, Moodle
from modules.moodle.models import MoodleCourse, MoodleCourseWithAssigns, MoodleGradesTable
from modules.pm_api.api import PocketMoodleAPI
from modules.pm_api.models import User


@profile
async def check_updates(user: User) -> str:
    extended_user = ExtendedUser(
        user_id=user.user_id,
        api_token=user.api_token,
        register_date=user.register_date,
        mail=user.mail,
        last_active=user.last_active,
        moodle_id=user.moodle_id,
        courses=(await PocketMoodleAPI().get_courses(user.user_id)),
        msg=None,
        is_admin=user.is_admin,
        is_manager=user.is_manager,
    )
    settings = await PocketMoodleAPI().get_settings(extended_user.user_id)

    moodle = Moodle(extended_user, await PocketMoodleAPI().get_notification_status(extended_user.user_id))
    if not extended_user.moodle_id:
        extended_user.moodle_id = (await moodle.get_users_by_field(extended_user.mail))[0]["id"]
        if not extended_user.moodle_id:
            return "Cannot get Moodle ID"
        await PocketMoodleAPI().set_moodle_id(extended_user.user_id, extended_user.moodle_id)

    moodle_courses: list[MoodleCourse] = await moodle.get_courses()
    active_courses_ids = await moodle.get_active_courses_ids(moodle_courses)
    course_ids = [int(course.id) for course in moodle_courses]
    if not (moodle.notification_status.is_update_requested or moodle.notification_status.is_newbie_requested):
        course_ids = active_courses_ids

    await moodle.add_new_courses(moodle_courses, active_courses_ids)

    courses_grades_table: list[MoodleGradesTable] = await asyncio.gather(
        *[moodle.get_grades(course_id) for course_id in course_ids]
    )
    await moodle.set_grades(courses_grades_table, course_ids)
    if not settings.status or not settings.notification_grade:
        moodle.new_grades, moodle.updated_grades = [], []

    courses_assigns: list[MoodleCourseWithAssigns] = await moodle.get_assignments()
    await moodle.set_assigns(courses_assigns)
    if not settings.status or not settings.notification_deadline:
        moodle.updated_deadlines, moodle.new_deadlines, moodle.upcoming_deadlines = [], [], []

    if moodle.notification_status.is_newbie_requested:
        moodle.new_grades, moodle.updated_grades = [], []
        moodle.updated_deadlines, moodle.new_deadlines, moodle.upcoming_deadlines = [], [], []

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

    if moodle.notification_status.is_update_requested:
        await send(moodle.user.user_id, "Updated\!")
        moodle.notification_status.is_update_requested = False
    elif moodle.notification_status.is_newbie_requested:
        moodle.notification_status.is_newbie_requested = False
        await send(moodle.user.user_id, "Your courses are *ready*\!")

    await PocketMoodleAPI().set_notification_status(extended_user.user_id, moodle.notification_status)

    del extended_user
    del moodle
    return "Success"
