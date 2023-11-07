import asyncio
from copy import copy, deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup

from config import IS_PROXY
from functions.bot import send
from functions.functions import clear_MD, get_diff_time, replace_grade_name
from modules.database import CourseDB, DeadlineDB, GradeDB

from ..database.models import Course, NotificationStatus
from ..database.models import User as UserModel
from . import exceptions


@dataclass
class User(UserModel):
    id: int
    courses: dict[str, Course]
    msg: str


class Moodle():
    def __init__(self, user, proxy_dict: dict, notifications: NotificationStatus) -> None:
        self.user: User = user
        self.host = 'https://moodle.astanait.edu.kz/'
        self.user.msg = None
        self.proxy_dict = proxy_dict
        self.notifications = notifications

    async def check(self):
        try:
            await self.check_api_token()
        except exceptions.WrongToken:
            if self.notifications.error_check_token:
                text = f"Wrong *Moodle Key*, seems like you need to try register one more time❗️"
                await send(self.user.user_id, text, True)
            return False
        except exceptions.WrongMail:
            if self.notifications.error_check_token:
                text = f"*Email* or *Barcode* not valid, seems like you need to try register one more time❗️"
                await send(self.user.user_id, text, True)
            return False
        except exceptions.MoodleConnectionFailed:
            return False
        except exceptions.TimeoutMoodle:
            return False
        except:
            return False  
        else:
            return True

    async def make_request(self, function=None, token=None, params=None, headers=None, is_du=False, host='https://moodle.astanait.edu.kz', end_point='/webservice/rest/server.php/') -> dict:
        if not token:
            token = self.user.api_token
        if is_du:
            args = params
        else:
            args = {'moodlewsrestformat': 'json', 'wstoken': token, 'wsfunction': function}
            if params:
                args.update(params)
        timeout = aiohttp.ClientTimeout(total=5)
        proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
        async with aiohttp.ClientSession(host, timeout=timeout, headers=headers) as session:
            if args:
                r = await session.get(end_point, params=args, proxy=proxy)
            else:
                r = await session.get(end_point, proxy=proxy)
            return await r.json()

    async def get_users_by_field(self, value: str, field: str = "email") -> dict:
        f = 'core_user_get_users_by_field'
        params = {
            'field': field,
            'values[0]': value
        }
        return await self.make_request(function=f, params=params)

    async def check_api_token(self):
        result: list | dict  = await self.get_users_by_field(value=self.user.mail, field='email')
            
        if result.get('errorcode') == 'invalidtoken':
            raise exceptions.WrongToken
        if result.get('errorcode') == 'invalidparameter':
            raise exceptions.WrongMail
            
        if len(result) != 1:
            raise exceptions.WrongMail

    async def get_courses(self):
        f = 'core_enrol_get_users_courses'
        if self.user.id is None:
            self.user.id = (await self.get_users_by_field(value=self.user.mail))[0]['id']
        params = {
            'userid': self.user.id 
        }
        return await self.make_request(f, params=params)

    async def get_grades(self, courseid):
        f = 'gradereport_user_get_grades_table'
        if not self.user.id:
            self.user.id = (await self.get_users_by_field(self.user.mail))[0]['id']

        params = {
            'userid': self.user.id,
            'courseid': courseid
        }
        return await self.make_request(f, params=params)

    async def get_assignments(self):
        f = 'mod_assign_get_assignments'
        return await self.make_request(f)
    
    async def is_assignment_submitted(self, id):
        f = 'mod_assign_get_submission_status'
        params = {
            'assignid': id,
        }
        data = await self.make_request(f, params=params)
        status = data.get('lastattempt', {}).get('submission', {}).get('status', None)
        if status == "submitted":
            return True, id
        return False, id        

    async def get_active_courses_ids(self, courses) -> tuple[int]:
        active_courses_ids = []
        for course in courses:
            now = datetime.now()
            # start_date = datetime.utcfromtimestamp(course['startdate']) + timedelta(hours=6)
            end_date = datetime.utcfromtimestamp(course['enddate']) + timedelta(hours=6)
            if now < end_date:
            # if now > start_date and now < end_date:
                active_courses_ids.append(int(course['id']))
        return active_courses_ids
    
    async def add_new_courses(self, courses, active_courses_ids):
        for course in courses:
            course_id = course['id']
            active = True if int(course_id) in active_courses_ids else False
            
            if str(course_id) not in self.user.courses:
                await CourseDB.set_course(
                    user_id=self.user.user_id,
                    course_id=int(course_id),
                    name=course['shortname'],
                    active=active
                )
            else:
                if self.user.courses[str(course_id)].active != active:
                    await CourseDB.update_course(user_id=self.user.user_id, course_id=course_id, active=active)
        await CourseDB.commit()

    async def set_grades(self, courses_grades, course_ids):
        new_grades = ['New grades:']
        updated_grades = ['Updated grades:']

        index_new = 0
        index_updated = 0

        moodle = 'https://moodle.astanait.edu.kz'

        list_ids = {
            'Register Midterm': '0',
            'Register Endterm': '1',
            'Register Term': '2',
            'Register Final': '3',
            'Course total': '4',
        }

        for course_grades in [ _ for _ in courses_grades if 'tables' in _ and int(_['tables'][0]['courseid']) in course_ids ]:
            course_grades = course_grades['tables'][0]
            course = self.user.courses[str(course_grades['courseid'])]
            url_to_course = f"{moodle}/grade/report/user/index.php?id={course.course_id}"

            for grade in course_grades['tabledata']:

                if grade.__class__ is list or len(grade) in [0,2]:
                    continue

                name = replace_grade_name(BeautifulSoup(grade['itemname']['content'], 'lxml').text)
                id = str(grade['itemname']['id'].split('_')[1])
                if name in list_ids:
                    id = str(list_ids[name])
                percentage: str = grade['percentage']['content'].replace(',', '.')

                if id not in course.grades.keys():
                    if '%' in percentage:
                        if clear_MD(course.name) not in new_grades[index_new]:
                            new_grades[index_new] += f"\n\n  [{clear_MD(course.name)}]({clear_MD(url_to_course)}):"
                        new_grades[index_new] += f"\n      {clear_MD(name)} / *{clear_MD(percentage)}*"
                        if len(new_grades[index_new]) > 3000:
                            index_new += 1
                            new_grades.append('')

                    await GradeDB.set_grade(
                        user_id=self.user.user_id,
                        course_id=course.course_id,
                        grade_id=int(id),
                        name=name,
                        percentage=percentage
                    )

                elif id in course.grades.keys() and str(percentage) != str(course.grades[id].percentage):
                    old_grade = course.grades[id].percentage
                    if percentage != 'Error' and not (percentage == '-' and old_grade == 'Error'):
                        if clear_MD(course.name) not in updated_grades[index_updated]:
                            updated_grades[index_updated] += f"\n\n  [{clear_MD(course.name)}]({clear_MD(url_to_course)}):"
                        updated_grades[index_updated] += f"\n      {clear_MD(name)} / {clear_MD(old_grade)} \-\> *{clear_MD(percentage)}*"
                        if len(updated_grades[index_updated]) > 3000:
                            index_updated += 1
                            updated_grades.append('')

                    await GradeDB.update_grade(
                        user_id=self.user.user_id,
                        course_id=course.course_id,
                        grade_id=int(id),
                        percentage=percentage
                    )

        return [new_grades, updated_grades]
    
    async def set_assigns(self, courses_assigns):
        updated_deadlines = ['Updated deadlines:']
        new_deadlines = ['New deadlines:']
        upcoming_deadlines = ['Upcoming deadlines:']

        index_updated = 0
        index_new = 0
        index_upcoming = 0
        
        for course_assigns in [ cs for cs in courses_assigns if self.user.courses[str(cs['id'])].active ]:
            course_state1 = 0
            course_state2 = 0
            course_state3 = 0
            
            course = self.user.courses[str(course_assigns['id'])]
            course_name = clear_MD(course.name)
            url_to_course = f"/course/view.php?id={course.course_id}"

            assignment_ids_to_check = [str(assign['id']) for assign in course_assigns['assignments']]

            check_tasks = [self.is_assignment_submitted(assign_id) for assign_id in assignment_ids_to_check]
            results = await asyncio.gather(*check_tasks)
            submitted_dict = {
                id: submitted for submitted, id in results 
            }

            for assign in course_assigns['assignments']:
                assign_id = str(assign['id'])
                assignment_id = str(assign['cmid'])
                assignment_name = assign['name']
                assignment_due = (datetime.utcfromtimestamp(assign['duedate']) + timedelta(hours=6)).strftime('%A, %d %B %Y, %I:%M %p')
                assignment_graded = bool(int(assign['grade']))

                submitted = submitted_dict[assign_id]
                
                url_to_assign = f'https://moodle.astanait.edu.kz/mod/assign/view.php?id={assignment_id}'
                
                if assignment_id not in course.deadlines:
                    if not submitted:
                        diff_time = get_diff_time(assignment_due)
                        if diff_time > timedelta(days=0):
                            if not course_state1:
                                course_state1 = 1
                                new_deadlines[index_new] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                            new_deadlines[index_new] += f"\n      [{clear_MD(assignment_name)}]({clear_MD(url_to_assign)})"
                            new_deadlines[index_new] += f"\n      {clear_MD(assignment_due)}"
                            new_deadlines [index_new]+= f"\n      Remaining: {clear_MD(diff_time)}\n"
                            if len(new_deadlines[index_new]) > 3000:
                                index_new += 1
                                new_deadlines.append('')

                    await DeadlineDB.set_deadline(
                        user_id=self.user.user_id,
                        course_id=course.course_id,
                        id=int(assignment_id),
                        assign_id=int(assign_id),
                        name=assignment_name,
                        due=datetime.strptime(assignment_due, "%A, %d %B %Y, %I:%M %p"),
                        graded=assignment_graded,
                        submitted=submitted,
                        status={
                            'status03': 0,
                            'status1': 0,
                            'status2': 0,
                            'status3': 0
                        }
                    )
                else:
                    assign = course.deadlines[assignment_id]
                    assign.assign_id = assign_id
                    diff_time = get_diff_time(assignment_due)
                    assign.graded = assignment_graded
                    assign.submitted = submitted
                    old_status = deepcopy(assign.status)

                    if not submitted:
                        if assignment_due != assign.due.strftime('%A, %d %B %Y, %I:%M %p'):
                            if not course_state2:
                                course_state2 = 1
                                updated_deadlines[index_updated] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                            updated_deadlines[index_updated] += f"\n      [{clear_MD(assign.name)}]({clear_MD(url_to_assign)})"
                            updated_deadlines[index_updated] += f"\n      {clear_MD(assignment_due)}"
                            updated_deadlines[index_updated] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                            if len(updated_deadlines[index_updated]) > 3000:
                                index_updated += 1
                                updated_deadlines.append('')

                        reminders_filter = [
                            ['status03', timedelta(hours=3)],
                            ['status1', timedelta(days=1)],
                            ['status2', timedelta(days=2)],
                            ['status3', timedelta(days=3)],
                        ]

                        for i, _ in enumerate(reminders_filter):
                            key, td = reminders_filter[i]
                            if not assign.status.get(key, 0) and diff_time>timedelta(hours=1) and diff_time<td:
                                if not course_state3:
                                    course_state3 = 1
                                    upcoming_deadlines[index_upcoming] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                                upcoming_deadlines[index_upcoming] += f"\n      [{clear_MD(assign.name)}]({clear_MD(url_to_assign)})"
                                upcoming_deadlines[index_upcoming] += f"\n      {clear_MD(assignment_due)}"
                                upcoming_deadlines[index_upcoming] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                                if len(upcoming_deadlines[index_upcoming]) > 3000:
                                    index_upcoming += 1
                                    upcoming_deadlines.append('')
                                for _ in range(i, 4):
                                    key, td = reminders_filter[_]
                                    assign.status[key] = 1
                                break

                    if assignment_due != assign.due.strftime('%A, %d %B %Y, %I:%M %p') or old_status != assign.status or assign.submitted != submitted:
                        await DeadlineDB.update_deadline(
                            user_id=self.user.user_id,
                            course_id=course.course_id,
                            id=int(assignment_id),
                            name=assignment_name,
                            due=datetime.strptime(assignment_due, "%A, %d %B %Y, %I:%M %p"),
                            graded=assignment_graded,
                            submitted=submitted,
                            status=assign.status
                        )

        return [updated_deadlines, new_deadlines, upcoming_deadlines]       

    async def set_gpa(self, gpa):
        avg_gpa = gpa['averageGpa']
        all_credits_sum = gpa['allCreditsSum']
        gpa_dict = {}
        for key, val in gpa['gpaOfTrimesters'].items():
            if key == "0":
                gpa_dict[f"Summer Trimester GPA"] = val
            else:
                gpa_dict[f"Trimester {key} GPA"] = val
        gpa_dict['Average performance GPA'] = avg_gpa

        self.user.gpa = gpa_dict
            
    async def set_curriculum(self, curriculum):
        self.user.curriculum = {
            '1': {'1': {}, '2': {}, '3': {}},
            '2': {'1': {}, '2': {}, '3': {}},
            '3': {'1': {}, '2': {}, '3': {}},
        }
        for component in curriculum:
            id = str(component['id'])
            year = str(component['curriculum']['year'])
            trimester = str(component['curriculum']['numberOfTrimester'])
            discipline = {
                'id': id,
                'name': component['curriculum']['discipline']['titleEn'],
                'credits': component['curriculum']['discipline']['volumeCredits'],
            }
            self.user.curriculum[year][trimester][id] = discipline

    async def get_gpa(self):
        headers = {
            "Authorization": f"Bearer {self.user.token_du}",
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Origin': 'https://du.astanait.edu.kz',
            'Referer': 'https://du.astanait.edu.kz/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }
        return await self.make_request(headers=headers, is_du=True, host="https://du.astanait.edu.kz:8765", end_point="/astanait-office-module/api/v1/academic-department/assessment-report/transcript-gpa-for-student")

    async def get_curriculum(self, course_num: int):
        headers = {
            "Authorization": f"Bearer {self.user.token_du}",
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Origin': 'https://du.astanait.edu.kz',
            'Referer': 'https://du.astanait.edu.kz/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }
        
        params = {
            'course': course_num
        }
        return await self.make_request(headers=headers, params=params, is_du=True, host="https://du.astanait.edu.kz:8765", end_point="/astanait-office-module/api/v1/student-discipline-choose/get-student-IC-by-course-for-student")
