import asyncio
import os

import dotenv

from functions import aioredis
from functions.functions import timeit
from moodle_module import Moodle, UserType


@timeit
async def main():
    user: UserType = await aioredis.get_user(626591599)

    if user.is_registered_moodle:
        moodle = Moodle(user)
        await moodle.check()

        if moodle.user.login_status and moodle.user.token:
            courses = await moodle.get_courses()
            active_courses_ids = await moodle.get_active_courses_ids()
            course_ids = list(course['id'] for course in courses)
            print(type(active_courses_ids[0]))
            print(type(courses[0]['id']))

            courses_ass = (await moodle.get_assignments())['courses']
            courses_grades = await asyncio.gather(*[moodle.get_grades(course_id) for course_id in course_ids])

            # moodle.add_new_courses(courses, active_courses_ids)


            return 'Success'
        else:
            return user.msg


dotenv.load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_DB = os.getenv('REDIS_DB')
REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASSWD = os.getenv('REDIS_PASSWD')

asyncio.run(aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
))
print(asyncio.run(main()))
asyncio.run(aioredis.close())

