import asyncio
from datetime import datetime, timedelta
import os
import re
from bs4 import BeautifulSoup


async def auth_moodle(data, s):
    login, password = data.values()
    async with s.get("/login/index.php", timeout=15) as r_1:
        text = await r_1.text()
        pattern_auth = '<input type="hidden" name="logintoken" value="\w{32}">'
        token = re.findall(pattern_auth, text)
        token = re.findall("\w{32}", token[0])[0]

        payload = {'anchor': '', 'logintoken': token, 'username': login,
                   'password': password, 'rememberusername': 1}
    async with s.post("/login/index.php", data=payload, timeout=15) as r_2:
        text = await r_2.read()
        if "Invalid login" in str(text):
            return 0
        else:
            return 1
            

async def get_courses(s):
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
    
    async with s.get(url_courses, timeout=15) as request:
        text = await request.read()
        soup = BeautifulSoup(text.decode('utf-8'), 'html.parser')

        div = soup.find("div", {"class": "profile_tree"})
        section = div.find_all("section", {"class": "node_category"})[2]
        ul = section.find("ul")
        ul = ul.find("ul")
        urls = ul.find_all("a")

        courses_id = []
        courses_name = []
        for course in urls:
            id = str(course.get("href")).split('course=')[1].split('&')[0]
            courses_id.append(id)
            name = str(str(course.text).partition(' | ')[0]).replace(
                "/", " ").replace(".", " ")
            courses_name.append(name)

        return courses_id, courses_name, active_courses_ids


def clear_courses(user, courses_ids, active_courses_ids):
    dict = user.get('courses', {})
    courses = []
    try:
        # for x in range(0, len(dict['courses'])):
        for key in dict.keys():
            dict[key]['active'] = dict[key]['id'] in active_courses_ids
            if dict[key]['id'] in courses_ids:
                courses.append(dict[key]['id'])
            else:
                del dict[key]
                break
    except:
        pass
    user['courses'] = dict
    return courses


def add_new_courses(user, courses_names, courses_ids, courses):
    for i in range(0, len(courses_names)):
        course = {
            'id': courses_ids[i],
            'name': courses_names[i],
            'grades': {},
            'assignments': {},
        }
        if courses_ids[i] not in courses:
            user['courses'][courses_ids[i]] = course


def add_new_courses_deadlines(courses_names, courses_ids, courses, deadlines):
    for i in range(0, len(courses_names)):
        course = {
            'id': courses_ids[i],
            'name': courses_names[i],
            'grades': {},
            'assignments': {}
        }
        if courses_ids[i] not in courses:
            deadlines['courses'][courses_ids[i]] = course

    return deadlines


async def get_grades_of_course(session, user, key):
    new_grades = ''
    updated_grades = ''
    moodle = 'https://moodle.astanait.edu.kz'
    url_to_course = f"/grade/report/user/index.php?id={user['courses'][key]['id']}"

    async with session.get(url_to_course, timeout=15) as request:
        rText = await request.read()
        soup = BeautifulSoup(rText.decode('utf-8'), 'html.parser')
        tbody = soup.find('tbody')

        rows = tbody.find_all('tr')

        percentages = {}
        for x in user['courses'][key]['grades']:
            percentages[user['courses'][key]['grades'][x]['id']] = user['courses'][key]['grades'][x]['percentage']

        list_ids = {
            'Register Midterm': 0,
            'Register Endterm': 1,
            'Register Term': 2,
            'Register Final': 3,
            'Course total': 4,
        }

        temp_rows = []
        for row in rows:
            try:
                row.find('span', {'class': 'gradeitemheader'}).get('title')
            except:
                continue
            else:
                temp_rows.append(row)
        for row in temp_rows:
            col_name = str(row.find('th', {'class': 'column-itemname'}).contents[0].text)
            try: _id = list_ids[col_name]
            except: continue
            col_percentage = str(row.find('td', {'class': 'column-percentage'}).text)
            temp = {'name': col_name, 'percentage': col_percentage, 'id': _id}
            if _id not in percentages.keys():
                if not user['ignore'] and '%' in col_percentage:
                    if f"\n\n  {user['courses'][key]['name']}:" not in new_grades:
                        new_grades += f"\n\n  {user['courses'][key]['name']}:"
                    new_grades += f"\n      - [{col_name}]({moodle+url_to_course}) / {col_percentage}"
                user['courses'][key]['grades'][_id] = temp
            elif _id in percentages.keys() and str(col_percentage) != str(percentages[_id]):
                old_grade = user['courses'][key]['grades'][x]['percentage']
                user['courses'][key]['grades'][x]['percentage'] = col_percentage
                if f"\n\n  {user['courses'][key]['name']}:" not in updated_grades:
                    updated_grades += f"\n\n  {user['courses'][key]['name']}:"
                updated_grades += f"\n      - [{col_name}]({moodle+url_to_course}) / {old_grade} -> {col_percentage}"

        for row in rows:
            try:
                id = str(row.find('a').get('href')).split('?id=')[1].split('&')[0]
                col_name = str(row.find('th', {'class': 'column-itemname'}).contents[0].text)
                col_percentage = str(row.find('td', {'class': 'column-percentage'}).text)
                temp = {'name': col_name, 'percentage': col_percentage, 'id': id}
                if id not in percentages.keys():
                    if not user['ignore'] and '%' in col_percentage:
                        if f"\n\n  {user['courses'][key]['name']}:" not in new_grades:
                            new_grades += f"\n\n  {user['courses'][key]['name']}:"
                        new_grades += f"\n      - [{col_name}]({moodle+url_to_course}) / {col_percentage}"
                    user['courses'][key]['grades'][id] = temp
                elif id in percentages.keys() and str(col_percentage) != str(percentages[id]):
                    old_grade = user['courses'][key]['grades'][x]['percentage']
                    user['courses'][key]['grades'][x]['percentage'] = col_percentage
                    if f"\n\n  {user['courses'][key]['name']}:" not in updated_grades:
                        updated_grades += f"\n\n  {user['courses'][key]['name']}:"
                    updated_grades += f"\n      - [{col_name}]({moodle+url_to_course}) / {old_grade} -> {col_percentage}"
            except Exception as exc:
                # print(user['courses'][key]['name'], exc)
                continue
    return [new_grades, updated_grades]


def black_list(assignment_name):
    list = ['midterm','endterm','final', 'quiz', 'test']
    skip = False
    for item in list:
        if item in assignment_name.lower():
            skip = True
            break
    return skip


async def get_att_stat(s, data, i, att_id):
    href = f'/mod/attendance/view.php?mode=2&sesscourses=all&id={att_id}&view=5'
    async with s.get(href, timeout=15) as request:
        text = await request.text()
        soup = BeautifulSoup(text, 'html.parser')
        table = soup.find('table')
        c0_arr = table.find_all('td', {'class':'cell c0'})
        c1_arr = table.find_all('td', {'class':'cell c1 lastcol'})
        
        data['courses'][i]['attendance'] = {}
        data['att_statistic'] = {}
        for j in range(0, len(c0_arr)):
            text = str(c0_arr[j].getText().replace(':', ''))
            data['att_statistic'][text] = int(c1_arr[j].getText())


async def get_assignment_due(assignment, s):
    id = str(assignment.get("id").split("-")[1])
    url_to_assign = f"/mod/assign/view.php?id={id}"
    async with s.get(url_to_assign, timeout=15) as request:
        text = await request.read()
        soup = BeautifulSoup(text.decode('utf-8'), 'html.parser')

        dates = soup.find('div', {'data-region': 'activity-dates'})
        divs = dates.find_all('div')
        for div in divs:
            due_text = div.text
            if 'Due:' in due_text:
                due = due_text.replace('\n', '').replace('Due: ', '').replace('            ', '')
                break

        g_table = soup.find('table', {'class': 'generaltable'})
        col1 = g_table.find_all('th')
        col2 = g_table.find_all('td')

        table = {}
        for i in range(0, len(col1)):
            table[col1[i].text] = col2[i].text

        state = 0
        if 'Submitted for grading' == table['Submission status']:
            state = 1

        return id, due, state


async def get_attendance(soup, s, data, i):
    for item in soup.find_all('a', {'class': 'aalink'}):
        if 'attendance' in item.get('href'):
            att_id = item.get('href').replace('https://moodle.astanait.edu.kz/mod/attendance/view.php?id=', '')
            await asyncio.sleep(5)
            if os.getenv('ATT_STATE') == "1":
                os.environ["ATT_STATE"] = "0"
                await get_att_stat(s, data, i, att_id)

            href = (item.get('href')+'&view=5').replace('https://moodle.astanait.edu.kz', '')
            async with s.get(href, timeout=15) as request:
                text2 = await request.text()
                soup2 = BeautifulSoup(text2, 'html.parser')
                table = soup2.find('table', {'class':'attlist'})
                c0_arr = table.find_all('td', {'class':'cell c0'})
                c1_arr = table.find_all('td', {'class':'cell c1 lastcol'})

                data['courses'][i]['attendance'] = {}
                for j in range(0, len(c0_arr)):
                    text = str(c0_arr[j].getText().replace(':', ''))
                    data['courses'][i]['attendance'][text] = c1_arr[j].getText()
                break


def chop_microseconds(delta):
    return delta - timedelta(microseconds=delta.microseconds)


def get_diff_time(time_str):
    due = datetime.strptime(time_str, '%A, %d %B %Y, %I:%M %p')
    now = datetime.now()
    diff = due-now
    return chop_microseconds(diff)
    

async def get_assignments_of_course(s, user, key, proxy):
    course_state1 = 0
    course_state2 = 0
    course_state3 = 0
    updated_deadlines = ''
    new_deadlines = ''
    upcoming_deadlines = ''

    url = 'https://moodle.astanait.edu.kz/mod/assign/view.php?id='
    url_to_course = f"/course/view.php?id={user['courses'][key]['id']}"

    assignments_ids = []
    for assignment in user['courses'][key]['assignments']:
        assignments_ids.append(user['courses'][key]['assignments'][assignment]['id'])

    async with s.get(url_to_course, timeout=15, proxy=proxy) as request:
        text = await request.text()
        soup = BeautifulSoup(text, 'html.parser')

        assignments1 = soup.find_all(
        'li', {"class": "activity assign modtype_assign hasinfo"})
        assignments2 = soup.find_all(
            'li', {"class": "activity assign modtype_assign"})
        assignments = assignments1 + assignments2

        await asyncio.sleep(5)
        await get_attendance(soup, s, user, key)

        for assignment in assignments:
            try:
                assignment_name = str(assignment.find('span', {'class': 'instancename'}).text).lower()
                
                assignment_id, assignment_due, assignment_sub = await get_assignment_due(assignment, s)
                if assignment_id == 0:
                    continue
                if assignment_id not in assignments_ids:
                    assignment_dict = {
                        'id': assignment_id,
                        'name': assignment_name,
                        'due': assignment_due,
                        'submitted': assignment_sub,
                        'status': 0
                    }
                    user['courses'][key]['assignments'][assignment_id] = assignment_dict
                    assignments_ids.append(assignment_id)
                    diff_time = get_diff_time(assignment_due)
                    if not assignment_sub and not black_list(assignment_name):
                        if not course_state1:
                            course_state1 = 1
                            new_deadlines += f"\n\n  [{user['courses'][key]['name']}]({url_to_course}):"
                        new_deadlines += f"\n      [{assignment_dict['name']}]({url}{assignment_dict['id']})"
                        due = assignment_dict['due'].replace(', ','\n      ')
                        new_deadlines += f"\n      {due}"
                        new_deadlines += f"\n      Remaining: {diff_time}\n"
                else:
                    if not black_list(assignment_name):
                        for x in user['courses'][key]['assignments']:
                            if user['courses'][key]['assignments'][x]['id'] == assignment_id and assignment_sub != user['courses'][key]['assignments'][x]['submitted']:
                                user['courses'][key]['assignments'][x]['submitted'] = assignment_sub

                            if user['courses'][key]['assignments'][x]['id'] == assignment_id and assignment_due != user['courses'][key]['assignments'][x]['due']:
                                user['courses'][key]['assignments'][x]['due'] = assignment_due
                                user['courses'][key]['assignments'][x]['status'] = 0
                                diff_time = get_diff_time(user['courses'][key]['assignments'][x]['due'])
                                if not assignment_sub:
                                    if not course_state2:
                                        course_state2 = 1
                                        updated_deadlines += f"\n\n  [{user['courses'][key]['name']}]({url_to_course}):"
                                    updated_deadlines += f"\n      [{user['courses'][key]['assignments'][x]['name']}]({url}{assignment_id})"
                                    due = user['courses'][key]['assignments'][x]['due'].replace(', ','\n      ')
                                    updated_deadlines += f"\n      {due}"
                                    updated_deadlines += f"\n      Remaining: {diff_time}\n"
                            
                            diff_time = get_diff_time(user['courses'][key]['assignments'][x]['due'])
                            if not user['courses'][key]['assignments'][x]['status'] and diff_time>timedelta(days=0) and diff_time<timedelta(days=3):
                                if not assignment_sub:
                                    if not course_state3:
                                        course_state3 = 1
                                        upcoming_deadlines += f"\n\n  [{user['courses'][key]['name']}]({url_to_course}):"
                                    upcoming_deadlines += f"\n      [{user['courses'][key]['assignments'][x]['name']}]({url}{assignment_id})"
                                    due = user['courses'][key]['assignments'][x]['due'].replace(', ','\n      ')
                                    upcoming_deadlines += f"\n      {due}"
                                    upcoming_deadlines += f"\n      Remaining: {diff_time}\n"
                                    user['courses'][key]['assignments'][x]['status'] = 1
            except Exception as exc:
                # print(request, exc)
                # print(exc)
                continue
        return updated_deadlines, new_deadlines, upcoming_deadlines
