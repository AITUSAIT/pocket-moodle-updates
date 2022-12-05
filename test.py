import asyncio
from datetime import datetime
from datetime import timedelta
from pprint import pprint
import time
from functions import aioredis
from functions.functions import timeit
from moodle_module import Moodle, UserType
from config import (MAIN_HOST, REDIS_DB, REDIS_HOST, REDIS_PASSWD, REDIS_PORT,
                    REDIS_USER, token)


@timeit
async def check_updates():
    user: UserType = await aioredis.get_user(626591599)

    if user.is_registered_moodle:
        moodle = Moodle(user)
        await moodle.check()

        if moodle.user.login_status and moodle.user.token:
            calendar = {}

            year = datetime.now().year
            month = datetime.now().month
            next_year = (datetime.now() + timedelta(weeks=2)).year
            next_month = (datetime.now() + timedelta(weeks=2)).month
            years = set([year, next_year])
            months = set([month, next_month])

            for year in years:
                if not str(year) in calendar:
                    calendar[str(year)] = {}
                for month in months:
                    if not str(month) in calendar[str(year)]:
                        calendar[str(year)][str(month)] = {}
                    cal = await moodle.get_calendar(year, month)
                    for week in cal['weeks']:
                        for day in week['days']:
                            if not str(day['mday']) in calendar[str(year)][str(month)]:
                                calendar[str(year)][str(month)][day['mday']] = {'events': [], 'week_day': day['wday']}

                            for event in day['events']:
                                if 'Attendance' in event['name']:
                                    new_event = {
                                        'course': event['course'],
                                        'time_start': str(time.mktime((datetime.utcfromtimestamp(event['timestart']) + timedelta(hours=6)).timetuple())),
                                        'time_duration': event['timeduration']
                                    }
                                    calendar[str(year)][str(month)][day['mday']]['events'].append(new_event)
                


asyncio.run(aioredis.start_redis(
        REDIS_USER,
        REDIS_PASSWD,
        REDIS_HOST,
        REDIS_PORT,
        REDIS_DB
    ))
asyncio.run(check_updates())