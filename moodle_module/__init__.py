from datetime import datetime, timedelta
import os
import re

import aiohttp
from bs4 import BeautifulSoup

from functions.functions import clear_MD, get_diff_time, replace_grade_name, timeit

from .browser import get_cookies


class UserType:
    def __init__(self) -> None:
        self.user_id = None
        self.id = None

        self.token = None
        self.token_att = None
        self.cookies = None

        self.barcode = None
        self.passwd = None

        self.courses = None
        self.gpa = None
        self.att_statistic = None

        self.is_sub_grades = None
        self.is_sub_deadlines = None
        self.is_registered_moodle = None
        self.is_active_sub = None

        self.is_ignore = None

        self.login_status = None
        self.msg = None


class Moodle():
    def __init__(self, user: UserType) -> None:
        self.user: UserType = user
        self.host = 'https://moodle.astanait.edu.kz/'
        self.user.msg = None
        self.user.login_status = None


    async def check(self):
        if await self.check_cookies() is False:
            if str(self.user.barcode).isdigit():
                if int(self.user.barcode) >= 210000:
                    self.user.cookies, self.user.login_status, self.user.msg = await get_cookies(self.user.user_id, self.user.barcode, self.user.passwd)
                elif int(self.user.barcode) < 210000:
                    self.user.cookies, self.user.login_status = await self.auth_moodle()
                    if self.user.login_status:
                        self.user.msg = ''
                    else:
                        self.user.msg = 'Invalid login or password'
            else:    
                self.user.cookies, self.user.login_status, self.user.msg = await get_cookies(self.user.user_id, self.user.barcode, self.user.passwd)
        else:
            self.user.login_status = True

        if self.user.token is None:
            await self.get_and_set_token()


    async def auth_moodle(self):
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz') as s:
            async with s.get("/login/index.php", timeout=15) as r_1:
                text = await r_1.text()
                pattern_auth = '<input type="hidden" name="logintoken" value="\w{32}">'
                token = re.findall(pattern_auth, text)
                token = re.findall("\w{32}", token[0])[0]

                payload = {'anchor': '', 'logintoken': token, 'username': self.user.barcode,
                        'password': self.user.passwd, 'rememberusername': 1}
            async with s.post("/login/index.php", data=payload, timeout=15) as r_2:
                text = await r_2.read()
                if "Invalid login" in str(text):
                    return await s.cookie_jar.filter_cookies('https://moodle.astanait.edu.kz'), 0
                else:
                    return await s.cookie_jar.filter_cookies('https://moodle.astanait.edu.kz'), 1


    async def check_cookies(self):
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', cookies=self.user.cookies) as session:
            async with session.get("/login/index.php", timeout=15) as request:
                rText = await request.read()
                soup = BeautifulSoup(rText.decode('utf-8'), 'html.parser')
                if soup.find('input', {'id': 'username'}):
                    return False
                else:
                    return True


    async def get_and_set_token(self):
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', cookies=self.user.cookies) as session:
            async with session.get("/user/managetoken.php", timeout=15) as request:
                rText = await request.read()
                soup = BeautifulSoup(rText.decode('utf-8'), 'html.parser')
                div = soup.find('table', {'class': 'generaltable'})
                trs = div.find_all('tr')
                for tr in trs:
                    tds_0 = tr.find_all('td', {'class': 'cell c0'})
                    tds_1 = tr.find_all('td', {'class': 'cell c1'})
                    for i in range(0, len(tds_0)):
                        if tds_1[i].text == 'Moodle mobile web service':
                            self.user.token = tds_0[i].text


    async def make_request(self, function, token=None, params=None, end_point='webservice/rest/server.php/'):
        if not token:
            token = self.user.token
        args = {'moodlewsrestformat': 'json', 'wstoken': token, 'wsfunction': function}
        if params:
            args.update(params)
        async with aiohttp.ClientSession() as session:
            async with session.get(self.host + end_point, params=args) as r:
                try:
                    res = await r.json()
                except:
                    return await r.read()
                else:
                    return res


    async def get_active_courses_ids(self):
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', cookies=self.user.cookies) as s:
            async with s.get('/', timeout=15) as request:
                text = await request.read()
                soup = BeautifulSoup(text.decode('utf-8'), 'html.parser')
                profile_button = soup.find("a", {"data-title": "profile,moodle"})
                url_courses = profile_button.get("href") + '&showallcourses=1'
                url_courses = url_courses.replace('https://moodle.astanait.edu.kz', '')

                a = soup.find_all("a", {"data-type": "20"})
                active_courses_ids = []
                for course in a:
                    active_courses_ids.append(int(course.get("data-key")))
        return active_courses_ids
    
    
    async def add_new_courses(self, courses, active_courses_ids):
        for new_course in courses:
            if str(new_course['id']) not in self.user.courses.keys():
                self.user.courses[str(new_course['id'])] = {
                    'id': str(new_course['id']),
                    'name': new_course['shortname'],
                    'active': True if new_course['id'] in active_courses_ids else False,
                    'grades': {},
                    'assignments': {}
                }
    

    async def set_grades(self, courses_grades):
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

        for course_grades in courses_grades:
            course_grades = course_grades['tables'][0]
            course = self.user.courses[str(course_grades['courseid'])]
            url_to_course = f"{moodle}/grade/report/user/index.php?id={course['id']}"

            for grade in course_grades['tabledata']:

                if grade.__class__ is list or len(grade) in [0,2]:
                    continue

                name = replace_grade_name(BeautifulSoup(grade['itemname']['content'], 'lxml').text)
                id = str(grade['itemname']['id'].split('_')[1])
                if name in list_ids:
                    id = str(list_ids[name])
                percentage = grade['percentage']['content'].replace(',', '.')

                temp = {'name': name, 'percentage': percentage, 'id': id}
                if id not in course['grades'].keys():
                    if '%' in percentage:
                        if clear_MD(course['name']) not in new_grades[index_new]:
                            new_grades[index_new] += f"\n\n  [{clear_MD(course['name'])}]({clear_MD(url_to_course)}):"
                        new_grades[index_new] += f"\n      {clear_MD(name)} / {clear_MD(percentage)}"
                        if len(new_grades[index_new]) > 3000:
                            index_new += 1
                            new_grades.append('')

                    course['grades'][id] = temp
                elif id in course['grades'].keys() and str(percentage) != str(course['grades'][id]['percentage']):
                    old_grade = course['grades'][id]['percentage']
                    course['grades'][id]['percentage'] = percentage
                    if clear_MD(course['name']) not in updated_grades[index_updated]:
                        updated_grades[index_updated] += f"\n\n  [{clear_MD(course['name'])}]({clear_MD(url_to_course)}):"
                    updated_grades[index_updated] += f"\n      {clear_MD(name)} / {clear_MD(old_grade)} \-\> {clear_MD(percentage)}"
                    if len(updated_grades[index_updated]) > 3000:
                        index_updated += 1
                        updated_grades.append('')

        return [new_grades, updated_grades]
    

    async def set_assigns(self, courses_assigns):
        course_state1 = 0
        course_state2 = 0
        course_state3 = 0
        updated_deadlines = ['Updated deadlines:']
        new_deadlines = ['New deadlines:']
        upcoming_deadlines = ['Upcoming deadlines:']

        index_updated = 0
        index_new = 0
        index_upcoming = 0


        for course_assigns in courses_assigns:
            course = self.user.courses[str(course_assigns['id'])]
            course_name = clear_MD(course['name'])
            url_to_course = f"/course/view.php?id={course['id']}"

            for assign in course_assigns['assignments']:
                assignment_id = str(assign['id'])
                assignment_name = assign['name']
                assignment_due = datetime.utcfromtimestamp(assign['duedate']).strftime('%A, %d %B %Y, %I:%M %p')
                assignment_sub = bool(assign['nosubmissions'])
                assignment_graded = bool(assign['grade'])

                url_to_assign = f'https://moodle.astanait.edu.kz/mod/assign/view.php?id={assignment_id}'
                if assignment_id not in course['assignments']:
                    assignment_dict = {
                        'id': assignment_id,
                        'name': assignment_name,
                        'due': assignment_due,
                        'submitted': assignment_sub,
                        'status': 0
                    }
                    course['assignments'][assignment_id] = assignment_dict
                    diff_time = get_diff_time(assignment_due)
                    if not assignment_sub:
                        if not course_state1:
                            course_state1 = 1
                            new_deadlines[index_new] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                        new_deadlines[index_new] += f"\n      [{clear_MD(assignment_dict['name'])}]({clear_MD(url_to_assign)})"
                        new_deadlines[index_new] += f"\n      {clear_MD(assignment_due)}"
                        new_deadlines [index_new]+= f"\n      Remaining: {clear_MD(diff_time)}\n"
                        if len(new_deadlines[index_new]) > 3000:
                            index_new += 1
                            new_deadlines.append('')
                else:
                    assign = course['assignments'][assignment_id]

                    diff_time = get_diff_time(assign['due'])
                    if assign['id'] == assignment_id and assignment_sub != assign['submitted']:
                        assign['submitted'] = assignment_sub

                    if assign['id'] == assignment_id and assignment_due != assign['due']:
                        assign['due'] = assignment_due
                        assign['status'] = 0
                        if not assignment_sub:
                            if not course_state2:
                                course_state2 = 1
                                updated_deadlines[index_updated] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                            updated_deadlines[index_updated] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                            updated_deadlines[index_updated] += f"\n      {clear_MD(assignment_due)}"
                            updated_deadlines[index_updated] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                            if len(updated_deadlines[index_updated]) > 3000:
                                index_updated += 1
                                updated_deadlines.append('')

                    if assign['id'] == assignment_id and not assign['status'] and diff_time>timedelta(days=0) and diff_time<timedelta(days=3):
                        if not assignment_sub:
                            if not course_state3:
                                course_state3 = 1
                                upcoming_deadlines[index_upcoming] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                            upcoming_deadlines[index_upcoming] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                            upcoming_deadlines[index_upcoming] += f"\n      {clear_MD(assignment_due)}"
                            upcoming_deadlines[index_upcoming] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                            if len(upcoming_deadlines[index_upcoming]) > 3000:
                                index_upcoming += 1
                                upcoming_deadlines.append('')
                            assign['status'] = 1
        return [updated_deadlines, new_deadlines, upcoming_deadlines]       


    async def get_att_stat(self, s, att_id):
        href = f'/mod/attendance/view.php?mode=2&sesscourses=all&id={att_id}&view=5'
        async with s.get(href, timeout=15) as request:
            text = await request.text()
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find('table')
            c0_arr = table.find_all('td', {'class':'cell c0'})
            c1_arr = table.find_all('td', {'class':'cell c1 lastcol'})
            
            self.user.att_statistic = {}
            for j in range(0, len(c0_arr)):
                text = str(c0_arr[j].getText().replace(':', ''))
                self.user.att_statistic[text] = int(c1_arr[j].getText())


    async def get_attendance(self, course_id):
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', cookies=self.user.cookies) as s:
            async with s.get(f'/course/view.php?id={course_id}', timeout=15) as request:
                text = await request.read()
                soup = BeautifulSoup(text, 'html.parser')
                li = soup.find('li', {'class': 'attendance'})
                item = li.find('a', {'class': 'aalink'})
                if 'attendance' in item.get('href'):
                    att_id = item.get('href').replace('https://moodle.astanait.edu.kz/mod/attendance/view.php?id=', '')
                    if os.getenv('ATT_STATE') == "1":
                        os.environ["ATT_STATE"] = "0"
                        await self.get_att_stat(s, att_id)

                href = (item.get('href')+'&view=5').replace('https://moodle.astanait.edu.kz', '')
                async with s.get(href, timeout=15) as request:
                    text = await request.text()
                    soup2 = BeautifulSoup(text, 'html.parser')
                    table = soup2.find('table', {'class':'attlist'})
                    c0_arr = table.find_all('td', {'class':'cell c0'})
                    c1_arr = table.find_all('td', {'class':'cell c1 lastcol'})

                    self.user.courses[str(course_id)]['attendance'] = {}
                    for j in range(0, len(c0_arr)):
                        text = str(c0_arr[j].getText().replace(':', ''))
                        self.user.courses[str(course_id)]['attendance'][text] = c1_arr[j].getText()

    # ok
    async def get_users_by_field(self):
        f = 'core_user_get_users_by_field'
        params = {
            'field': 'email',
            'values[0]': self.user.barcode + '@astanait.edu.kz'
        }
        return await self.make_request(f, params=params)


    # ok
    async def get_courses(self):
        f = 'core_enrol_get_users_courses'
        id = (await self.get_users_by_field())[0]['id']
        params = {
            'userid': id
        }
        return await self.make_request(f, params=params)


    # ok
    async def get_grades(self, courseid):
        f = 'gradereport_user_get_grades_table'
        if self.user.id is None:
            self.user.id = (await self.get_users_by_field())[0]['id']
        params = {
            'userid': self.user.id,
            'courseid': courseid
        }
        return await self.make_request(f, params=params)

    
    # ok
    async def get_assignments(self):
        f = 'mod_assign_get_assignments'
        return await self.make_request(f)


    # bad
    async def get_att_bad(self):
        f = 'mod_attendance_get_sessions'
        return await self.make_request(f, token=self.user.token_att, end_point='mod/attendance/externallib.php')
