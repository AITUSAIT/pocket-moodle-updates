from datetime import datetime, timedelta
import os
import re
import time

import aiohttp
from bs4 import BeautifulSoup
from config import IS_PROXY

from functions.functions import clear_MD, get_diff_time, replace_grade_name

from .browser import Browser


class UserType:
    def __init__(self) -> None:
        self.user_id = None
        self.id = None

        self.token = None
        self.token_att = None
        self.token_du = None
        self.cookies = None

        self.email = None
        self.barcode = None
        self.passwd = None

        self.curriculum = None
        self.courses = None
        self.gpa = None
        self.att_statistic = None

        self.is_sub_grades = None
        self.is_sub_deadlines = None
        self.is_registered_moodle = None
        self.is_active_sub = None

        self.is_ignore = None
        self.att_notify: int = None

        self.login_status = None
        self.msg = None


class Moodle():
    def __init__(self, user: UserType, proxy_dict: dict) -> None:
        self.user: UserType = user
        self.host = 'https://moodle.astanait.edu.kz/'
        self.user.msg = None
        self.user.login_status = None
        self.proxy_dict = proxy_dict

    async def check(self):
        if self.user.email is None:
           self.user.token = None 
        if self.user.token is None or type(await self.get_users_by_field('')) is not list:
            self.user.token = None
            if str(self.user.barcode).isdigit():
                if int(self.user.barcode) >= 210000 or int(self.user.barcode) < 200000:
                    proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
                    browser = Browser(proxy)
                    self.user.cookies, self.user.login_status, self.user.msg, self.user.token_du = await browser.get_cookies_moodle(self.user.user_id, self.user.barcode, self.user.passwd)
                    if self.user.login_status:
                        self.user.email = await self.get_email()
                elif int(self.user.barcode) < 210000:
                    self.user.cookies, self.user.login_status = await self.auth_moodle()
                    if self.user.login_status:
                        self.user.msg = ''
                        self.user.email = await self.get_email()
                    else:
                        self.user.msg = 'Invalid login or password'
            else:
                proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
                browser = Browser(proxy)
                self.user.cookies, self.user.login_status, self.user.msg, self.user.token_du = await browser.get_cookies_moodle(self.user.user_id, self.user.barcode, self.user.passwd)
                if self.user.login_status:
                    self.user.email = await self.get_email()
        else:
            self.user.login_status = True

        if self.user.token is None and self.user.login_status:
            await self.get_and_set_token()

    async def auth_moodle(self):
        proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz') as s:
            async with s.get("/login/index.php", timeout=15, proxy=proxy) as r_1:
                text = await r_1.text()
                pattern_auth = '<input type="hidden" name="logintoken" value="\w{32}">'
                token = re.findall(pattern_auth, text)
                token = re.findall("\w{32}", token[0])[0]

                payload = {'anchor': '', 'logintoken': token, 'username': self.user.barcode,
                        'password': self.user.passwd, 'rememberusername': 1}
            async with s.post("/login/index.php", data=payload, timeout=15, proxy=proxy) as r_2:
                text = await r_2.read()
                if "Invalid login" in str(text):
                    return {} , 0
                else:
                    return s.cookie_jar.filter_cookies('https://moodle.astanait.edu.kz'), 1

    async def get_email(self):
        proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz') as s:
            async with s.get("/user/profile.php", cookies=self.user.cookies, proxy=proxy) as req:
                text = await req.read()
                soup = BeautifulSoup(text, 'html.parser')
                profile_tree = soup.find('div', {'class': 'profile_tree'})
                contentnode = profile_tree.find('li', {'class': 'contentnode'})
                email = contentnode.find('a').text
                return email

    async def check_cookies(self):
        timeout = aiohttp.ClientTimeout(total=60)
        proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', timeout=timeout, cookies=self.user.cookies) as session:
            async with session.get("/login/index.php", timeout=15, proxy=proxy) as request:
                rText = await request.read()
                soup = BeautifulSoup(rText.decode('utf-8'), 'html.parser')
                if soup.find('input', {'id': 'username'}):
                    return False
                else:
                    return True

    async def get_and_set_token(self):
        timeout = aiohttp.ClientTimeout(total=60)
        proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
        async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', timeout=timeout, cookies=self.user.cookies) as session:
            async with session.get("/user/managetoken.php", timeout=15, proxy=proxy) as request:
                rText = await request.read()
                soup = BeautifulSoup(rText.decode('utf-8'), 'html.parser')
                tds_0 = soup.find_all('td', {'class': 'cell c0'})
                tds_1 = soup.find_all('td', {'class': 'cell c1'})
                for i in range(0, len(tds_0)):
                    if tds_1[i].text == 'Moodle mobile web service':
                        self.user.token = tds_0[i].text

    async def make_request(self, function=None, token=None, params=None, headers=None, is_du=False, host='https://moodle.astanait.edu.kz', end_point='/webservice/rest/server.php/') -> dict:
        if not token:
            token = self.user.token
        if is_du:
            args = params
        else:
            args = {'moodlewsrestformat': 'json', 'wstoken': token, 'wsfunction': function}
            if params:
                args.update(params)
        timeout = aiohttp.ClientTimeout(total=60)
        proxy = f"http://{self.proxy_dict['login']}:{self.proxy_dict['passwd']}@{self.proxy_dict['ip']}:{self.proxy_dict['http_port']}" if IS_PROXY else None
        async with aiohttp.ClientSession(host, timeout=timeout, headers=headers) as session:
            if args:
                r = await session.get(end_point, params=args, proxy=proxy)
            else:
                r = await session.get(end_point, proxy=proxy)
            return await r.json()

    async def get_active_courses_ids(self, courses) -> tuple[int]:
        active_courses_ids = []
        for course in courses:
            now = datetime.now()
            start_date = datetime.utcfromtimestamp(course['startdate']) + timedelta(hours=6)
            end_date = datetime.utcfromtimestamp(course['enddate']) + timedelta(hours=6)
            if now > start_date and now < end_date:
                active_courses_ids.append(course['id'])
        return active_courses_ids
    
    async def add_new_courses(self, courses, active_courses_ids):
        for course in courses:
            if str(course['id']) not in self.user.courses.keys():
                self.user.courses[str(course['id'])] = {
                    'id': str(course['id']),
                    'name': course['shortname'],
                    'active': True if int(course['id']) in active_courses_ids else False,
                    'grades': {},
                    'assignments': {}
                }
            else:
                self.user.courses[str(course['id'])]['active'] = True if int(course['id']) in active_courses_ids else False

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
            if 'tables' not in course_grades:
                continue
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
                        new_grades[index_new] += f"\n      {clear_MD(name)} / *{clear_MD(percentage)}*"
                        if len(new_grades[index_new]) > 3000:
                            index_new += 1
                            new_grades.append('')

                    course['grades'][id] = temp
                elif id in course['grades'].keys() and str(percentage) != str(course['grades'][id]['percentage']):
                    old_grade = course['grades'][id]['percentage']
                    course['grades'][id]['percentage'] = percentage
                    if percentage != 'Error' and not (percentage == '-' and old_grade == 'Error'):
                        if clear_MD(course['name']) not in updated_grades[index_updated]:
                            updated_grades[index_updated] += f"\n\n  [{clear_MD(course['name'])}]({clear_MD(url_to_course)}):"
                        updated_grades[index_updated] += f"\n      {clear_MD(name)} / {clear_MD(old_grade)} \-\> *{clear_MD(percentage)}*"
                        if len(updated_grades[index_updated]) > 3000:
                            index_updated += 1
                            updated_grades.append('')

        return [new_grades, updated_grades]
    
    async def set_assigns(self, courses_assigns, courses_ids):
        updated_deadlines = ['Updated deadlines:']
        new_deadlines = ['New deadlines:']
        upcoming_deadlines = ['Upcoming deadlines:']

        index_updated = 0
        index_new = 0
        index_upcoming = 0
        
        for course_assigns in [ cs for cs in courses_assigns if int(self.user.courses[str(cs['id'])]['id']) in courses_ids ]:
            course_state1 = 0
            course_state2 = 0
            course_state3 = 0
            
            course = self.user.courses[str(course_assigns['id'])]
            course_name = clear_MD(course['name'])
            url_to_course = f"/course/view.php?id={course['id']}"

            for assign in course_assigns['assignments']:
                assign_id = str(assign['id'])
                assignment_id = str(assign['cmid'])
                assignment_name = assign['name']
                assignment_due = (datetime.utcfromtimestamp(assign['duedate']) + timedelta(hours=6)).strftime('%A, %d %B %Y, %I:%M %p')
                assignment_graded = bool(int(assign['grade']))
                submitted = True if course['assignments'].get(assignment_id, {}).get('submitted', False) else await self.is_assignment_submitted(assign_id)

                if submitted:
                    continue
                
                url_to_assign = f'https://moodle.astanait.edu.kz/mod/assign/view.php?id={assignment_id}'
                
                if assignment_id not in course['assignments']:
                    assignment_dict = {
                        'assign_id': assign_id,
                        'id': assignment_id,
                        'name': assignment_name,
                        'due': assignment_due,
                        'graded': assignment_graded,
                        'submitted': submitted,
                        'status': 0
                    }
                    course['assignments'][assignment_id] = assignment_dict
                    diff_time = get_diff_time(assignment_due)
                    if diff_time > timedelta(days=0):
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
                    assign['assign_id'] = assign_id
                    diff_time = get_diff_time(assignment_due)
                    assign['graded'] = assignment_graded
                    assign['submitted'] = submitted

                    if assignment_due != assign['due']:
                        assign['due'] = assignment_due
                        assign['status'] = 0
                        if not course_state2:
                            course_state2 = 1
                            updated_deadlines[index_updated] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                        updated_deadlines[index_updated] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                        updated_deadlines[index_updated] += f"\n      {clear_MD(assignment_due)}"
                        updated_deadlines[index_updated] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                        if len(updated_deadlines[index_updated]) > 3000:
                            index_updated += 1
                            updated_deadlines.append('')

                    if not assign.get('status3', 0) and diff_time>timedelta(days=2) and diff_time<timedelta(days=3):
                        if not course_state3:
                            course_state3 = 1
                            upcoming_deadlines[index_upcoming] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                        upcoming_deadlines[index_upcoming] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                        upcoming_deadlines[index_upcoming] += f"\n      {clear_MD(assignment_due)}"
                        upcoming_deadlines[index_upcoming] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                        if len(upcoming_deadlines[index_upcoming]) > 3000:
                            index_upcoming += 1
                            upcoming_deadlines.append('')
                        assign['status3'] = 1
                    elif not assign.get('status2', 0) and diff_time>timedelta(days=1) and diff_time<timedelta(days=2):
                        if not course_state3:
                            course_state3 = 1
                            upcoming_deadlines[index_upcoming] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                        upcoming_deadlines[index_upcoming] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                        upcoming_deadlines[index_upcoming] += f"\n      {clear_MD(assignment_due)}"
                        upcoming_deadlines[index_upcoming] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                        if len(upcoming_deadlines[index_upcoming]) > 3000:
                            index_upcoming += 1
                            upcoming_deadlines.append('')
                        assign['status2'] = 1
                    elif not assign.get('status1', 0) and diff_time>timedelta(days=0) and diff_time<timedelta(days=1):
                        if not course_state3:
                            course_state3 = 1
                            upcoming_deadlines[index_upcoming] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                        upcoming_deadlines[index_upcoming] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                        upcoming_deadlines[index_upcoming] += f"\n      {clear_MD(assignment_due)}"
                        upcoming_deadlines[index_upcoming] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                        if len(upcoming_deadlines[index_upcoming]) > 3000:
                            index_upcoming += 1
                            upcoming_deadlines.append('')
                        assign['status1'] = 1
                    elif not assign.get('status03', 0) and diff_time>timedelta(hours=2) and diff_time<timedelta(hours=3):
                        if not course_state3:
                            course_state3 = 1
                            upcoming_deadlines[index_upcoming] += f"\n\n  [{course_name}]({clear_MD(url_to_course)}):"
                        upcoming_deadlines[index_upcoming] += f"\n      [{clear_MD(assign['name'])}]({clear_MD(url_to_assign)})"
                        upcoming_deadlines[index_upcoming] += f"\n      {clear_MD(assignment_due)}"
                        upcoming_deadlines[index_upcoming] += f"\n      Remaining: {clear_MD(diff_time)}\n"
                        if len(upcoming_deadlines[index_upcoming]) > 3000:
                            index_upcoming += 1
                            upcoming_deadlines.append('')
                        assign['status03'] = 1
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

    async def get_attendance(self, courses_grades, course_id):
        updated_att = 'Updated Attendance:'
        moodle = 'https://moodle.astanait.edu.kz'

        try:
            for course_grades in courses_grades:
                if 'tables' not in course_grades:
                    continue
                if course_id != course_grades['tables'][0]['courseid']:
                    continue
                for grade in course_grades['tables'][0]['tabledata']:
                    if grade.__class__ is list or len(grade) in [0,2]:
                        continue
                    name = replace_grade_name(BeautifulSoup(grade['itemname']['content'], 'lxml').text)
                    if 'attendance' != name.lower():
                        continue
                    att_id = BeautifulSoup(grade['itemname']['content'], 'lxml').find('a')['href'].split('=')[-1]
                    url_to_course = f"{moodle}/grade/report/user/index.php?id={course_id}"

                    href = f'/mod/attendance/view.php?id={att_id}&view=5'
                    timeout = aiohttp.ClientTimeout(total=60)
                    async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', timeout=timeout, cookies=self.user.cookies) as s:
                        async with s.get(href, timeout=15) as request:
                            if os.getenv('ATT_STATE') == "1":
                                os.environ["ATT_STATE"] = "0"
                                await self.get_att_stat(s, att_id)
                            text = await request.text()
                            soup2 = BeautifulSoup(text, 'html.parser')
                            table = soup2.find('table', {'class':'attlist'})
                            c0_arr = table.find_all('td', {'class':'cell c0'})
                            c1_arr = table.find_all('td', {'class':'cell c1 lastcol'})

                            old_att_dict = self.user.courses[str(course_id)].get('attendance', {})
                            self.user.courses[str(course_id)]['attendance'] = {}
                            for j in range(0, len(c0_arr)):
                                text = str(c0_arr[j].getText().replace(':', ''))
                                self.user.courses[str(course_id)]['attendance'][text] = c1_arr[j].getText()

                            set1 = set(self.user.courses[str(course_id)]['attendance'].items())
                            set2 = set(old_att_dict.items())
                            diff = set1 - set2
                            for item in diff:
                                key, val = item
                                if clear_MD(self.user.courses[str(course_id)]['name']) not in updated_att:
                                    updated_att += f"\n\n  [{clear_MD(self.user.courses[str(course_id)]['name'])}]({clear_MD(url_to_course)}):"
                                updated_att += f"\n      {clear_MD(key)} / {clear_MD(old_att_dict.get(key, '-'))} \-\> *{clear_MD(val)}*"
                        await s.close()
        except Exception as exc:
            # print('https://moodle.astanait.edu.kz'+href)
            print(exc)
            ...
        return updated_att

    async def get_attendance_old(self, course_id):
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession('https://moodle.astanait.edu.kz', timeout=timeout, cookies=self.user.cookies) as s:
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
        except Exception as exc:
            print(exc)

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

    # ok
    async def get_users_by_field(self, value: str, field: str = "email"):
        f = 'core_user_get_users_by_field'
        params = {
            'field': field,
            'values[0]': value
        }
        return await self.make_request(f, params=params)

    # ok
    async def get_courses(self):
        f = 'core_enrol_get_users_courses'
        if self.user.id is None:
            try:
                self.user.id = (await self.get_users_by_field(self.user.barcode+"@astanait.edu.kz"))[0]['id']
            except:
                self.user.id = (await self.get_users_by_field(self.user.email))[0]['id']
        params = {
            'userid': self.user.id 
        }
        return await self.make_request(f, params=params)

    # ok
    async def get_grades(self, courseid):
        f = 'gradereport_user_get_grades_table'
        if self.user.id is None:
            try:
                self.user.id = (await self.get_users_by_field(self.user.barcode+"@astanait.edu.kz"))[0]['id']
            except:
                self.user.id = (await self.get_users_by_field(self.user.email))[0]['id']
        params = {
            'userid': self.user.id,
            'courseid': courseid
        }
        return await self.make_request(f, params=params)

    # ok
    async def get_assignments(self):
        f = 'mod_assign_get_assignments'
        return await self.make_request(f)
    
    # ok
    async def is_assignment_submitted(self, id):
        f = 'mod_assign_get_submission_status'
        params = {
            'assignid': id,
        }
        data = await self.make_request(f, params=params)
        status = data.get('lastattempt', {}).get('submission', {}).get('status', None)
        if status is None or status == "submitted":
            return True
        return False        

    # bad
    async def get_att(self):
        f = 'mod_attendance_get_sessions'
        return await self.make_request(f, token=self.user.token_att, end_point='mod/attendance/externallib.php')

    # ok-bad
    async def get_posts(self):
        f = 'mod_forum_get_discussion_posts'
        params = {
            'sortby': 'id',
            'discussionid': 600
        }
        return await self.make_request(f, token=self.user.token_att, params=params)

    # ok
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

    # ok
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
