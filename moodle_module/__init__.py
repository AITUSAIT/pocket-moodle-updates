import re

import aiohttp
from bs4 import BeautifulSoup

from functions.functions import timeit

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
                    self.user.cookies, self.user.login_status = await self.auth_moodle(self)
                    if self.user.login_status:
                        self.user.msg = ''
                    else:
                        self.user.msg = 'Invalid login or password'
            else:    
                self.user.cookies, self.user.login_status, self.user.msg = await get_cookies(self.user.user_id, self.user.barcode, self.user.passwd)
        else:
            self.user.login_status = True

        if not self.user.token:
            await self.get_and_set_token()


    @timeit
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


    @timeit
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
                    tds = tr.find_all('td')
                    if tds[1].text == 'Moodle mobile web service':
                        self.user.token = tds[0].text



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
                    active_courses_ids.append(course.get("data-key"))
        return active_courses_ids


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


    async def get_att(self):
        ...


    async def add_new_courses(self, courses, active_courses_ids):
        for new_course in courses:
            if new_course['id'] not in self.user.courses.keys():
                self.user.courses[new_course['id']] = {
                    'id': new_course['id'],
                    'name': new_course['shortname'],
                    'active': True if new_course['id'] in active_courses_ids else False,
                    'grades': {},
                    'assignments': {}
                }
            