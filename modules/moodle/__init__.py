import asyncio
import traceback
from copy import copy, deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, MutableMapping

import aiohttp
from bs4 import BeautifulSoup

from config import IS_PROXY
from functions.bot import send
from functions.functions import clear_md, get_diff_time, replace_grade_name
from modules.database import CourseDB, DeadlineDB, GradeDB, NotificationDB
from modules.database.models import Course, Deadline, NotificationStatus
from modules.database.models import User as UserModel
from modules.moodle import exceptions
from modules.proxy_provider import ProxyProvider


@dataclass
class User(UserModel):
    id: int
    courses: dict[str, Course]
    msg: str


class Moodle:
    def __init__(self, user: User, notifications: NotificationStatus) -> None:
        self.user = user
        self.host = "https://moodle.astanait.edu.kz/"
        self.user.msg = None
        self.notifications = notifications

        self.new_grades = ["New grades:"]
        self.updated_grades = ["Updated grades:"]
        self.index_updated_grades = 0
        self.index_new_grades = 0
        self.course_state1_grades = 0
        self.course_state2_grades = 0

        self.updated_deadlines = ["Updated deadlines:"]
        self.new_deadlines = ["New deadlines:"]
        self.upcoming_deadlines = ["Upcoming deadlines:"]
        self.index_updated_assigns = 0
        self.index_new_assigns = 0
        self.index_upcoming_assigns = 0
        self.course_state1_assigns = 0
        self.course_state2_assigns = 0
        self.course_state3_assigns = 0

    async def check(self):
        try:
            await self.check_api_token()
        except exceptions.WrongToken:
            if not self.notifications.error_check_token:
                await NotificationDB.set_notification_status(self.user.user_id, "error_check_token", True)
                text = "Wrong *Moodle Key*, seems like you need to try register one more time❗️"
                await send(self.user.user_id, text, True)
            return False
        except exceptions.WrongMail:
            if not self.notifications.error_check_token:
                await NotificationDB.set_notification_status(self.user.user_id, "error_check_token", True)
                text = "*Email* or *Barcode* not valid, seems like you need to try register one more time❗️"
                await send(self.user.user_id, text, True)
            return False
        except exceptions.MoodleConnectionFailed:
            return False
        except exceptions.TimeoutMoodle:
            return False
        except Exception:
            return False
        return True

    async def make_request(
        self,
        function=None,
        token=None,
        params=None,
        headers=None,
        is_du=False,
        host="https://moodle.astanait.edu.kz",
        end_point="/webservice/rest/server.php/",
        timeout: int = 5,
    ) -> dict:
        if not token:
            token = self.user.api_token
        if is_du:
            args = params
        else:
            args = {"moodlewsrestformat": "json", "wstoken": token, "wsfunction": function}
            if params:
                args.update(params)
        timeout_total = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(host, timeout=timeout_total, headers=headers) as session:
            r = await session.get(end_point, params=args, proxy=str(ProxyProvider.get_proxy()) if IS_PROXY else None)
            return await r.json()

    async def get_users_by_field(self, value: str, field: str = "email") -> dict:
        f = "core_user_get_users_by_field"
        params = {"field": field, "values[0]": value}
        return await self.make_request(function=f, params=params, timeout=10)

    async def check_api_token(self):
        result: list | dict = await self.get_users_by_field(value=self.user.mail, field="email")

        if not isinstance(result, list):
            if result.get("errorcode") == "invalidtoken":
                raise exceptions.WrongToken
            if result.get("errorcode") == "invalidparameter":
                raise exceptions.WrongMail

        if len(result) != 1:
            raise exceptions.WrongMail

    async def get_courses(self):
        f = "core_enrol_get_users_courses"
        if self.user.id is None:
            self.user.id = (await self.get_users_by_field(value=self.user.mail))[0]["id"]
        params = {"userid": self.user.id}
        return await self.make_request(f, params=params, timeout=10)

    async def get_grades(self, courseid):
        f = "gradereport_user_get_grades_table"
        if not self.user.id:
            self.user.id = (await self.get_users_by_field(self.user.mail))[0]["id"]

        params = {"userid": self.user.id, "courseid": courseid}
        return await self.make_request(f, params=params)

    async def get_assignments(self):
        f = "mod_assign_get_assignments"
        return await self.make_request(f, timeout=10)

    async def is_assignment_submitted(self, assign_id):
        f = "mod_assign_get_submission_status"
        params = {
            "assignid": assign_id,
        }
        data = await self.make_request(f, params=params)
        status = data.get("lastattempt", {}).get("submission", {}).get("status", None)
        if status == "submitted":
            return True, assign_id
        return False, assign_id

    async def course_get_contents(self, course_id: int) -> dict[str, Any]:
        f = "core_course_get_contents"
        params = {
            "courseid": course_id,
        }
        return await self.make_request(function=f, params=params)

    async def get_active_courses_ids(self, courses) -> tuple[int]:
        active_courses_ids = []
        for course in courses:
            now = datetime.now()
            # start_date = datetime.utcfromtimestamp(course['startdate']) + timedelta(hours=6)
            end_date = datetime.utcfromtimestamp(course["enddate"]) + timedelta(hours=6)
            if now < end_date:
                # if now > start_date and now < end_date:
                active_courses_ids.append(int(course["id"]))
        return active_courses_ids

    async def add_new_courses(self, courses, active_courses_ids):
        for course in courses:
            course_id = course["id"]
            active = int(course_id) in active_courses_ids

            if str(course_id) not in self.user.courses:
                CourseDB.set_course(
                    user_id=self.user.user_id, course_id=int(course_id), name=course["shortname"], active=active
                )
            else:
                if self.user.courses[str(course_id)].active != active:
                    CourseDB.update_course_user_pair(user_id=self.user.user_id, course_id=course_id, active=active)
        await CourseDB.commit()

    async def set_grades(self, courses_grades, course_ids):
        self.new_grades = ["New grades:"]
        self.updated_grades = ["Updated grades:"]

        self.index_new_grades = 0
        self.index_updated_grades = 0

        moodle = "https://moodle.astanait.edu.kz"

        list_ids = {
            "Register Midterm": "0",
            "Register Endterm": "1",
            "Register Term": "2",
            "Register Final": "3",
            "Course total": "4",
        }

        for course_grades in [
            _ for _ in courses_grades if "tables" in _ and int(_["tables"][0]["courseid"]) in course_ids
        ]:
            course_grades = course_grades["tables"][0]
            course = self.user.courses[str(course_grades["courseid"])]
            url_to_course = f"{moodle}/grade/report/user/index.php?id={course.course_id}"

            for grade in course_grades["tabledata"]:

                if grade.__class__ is list or len(grade) in [0, 2]:
                    continue

                name = replace_grade_name(BeautifulSoup(grade["itemname"]["content"], "lxml").text)
                grade_id = str(grade["itemname"]["id"].split("_")[1])
                if name in list_ids:
                    grade_id = str(list_ids[name])
                percentage: str = grade["percentage"]["content"].replace(",", ".")

                if grade_id not in course.grades.keys():
                    if "%" in percentage:
                        if not self.course_state1_grades:
                            self.course_state1_grades = 1
                            self.new_grades[
                                self.index_new_grades
                            ] += f"\n\n  [{clear_md(course.name)}]({clear_md(url_to_course)}):"

                        self.new_grades[self.index_new_grades] += f"\n      {clear_md(name)} / *{clear_md(percentage)}*"

                        if len(self.new_grades[self.index_new_grades]) > 3000:
                            self.index_new_grades += 1
                            self.new_grades.append("")

                    await GradeDB.set_grade(
                        user_id=self.user.user_id,
                        course_id=course.course_id,
                        grade_id=int(grade_id),
                        name=name,
                        percentage=percentage,
                    )

                elif grade_id in course.grades.keys() and str(percentage) != str(course.grades[grade_id].percentage):
                    old_grade = course.grades[grade_id].percentage
                    if percentage != "Error" and not (percentage == "-" and old_grade == "Error"):
                        if not self.course_state2_grades:
                            self.course_state2_grades = 1
                            self.updated_grades[
                                self.index_updated_grades
                            ] += f"\n\n  [{clear_md(course.name)}]({clear_md(url_to_course)}):"

                        self.updated_grades[
                            self.index_updated_grades
                        ] += f"\n      {clear_md(name)} / {clear_md(old_grade)} \-\> *{clear_md(percentage)}*"

                        if len(self.updated_grades[self.index_updated_grades]) > 3000:
                            self.index_updated_grades += 1
                            self.updated_grades.append("")

                    await GradeDB.update_grade(
                        user_id=self.user.user_id,
                        course_id=course.course_id,
                        grade_id=int(grade_id),
                        percentage=percentage,
                    )

    def notify_new_deadline(self, course: Course, assign: dict[str, Any]):
        course_name = clear_md(course.name)
        url_to_course = f"/course/view.php?id={course.course_id}"

        cm_id = str(assign["cmid"])
        assign_name = assign["name"]
        assign_due = (datetime.utcfromtimestamp(assign["duedate"]) + timedelta(hours=6)).strftime(
            "%A, %d %B %Y, %I:%M %p"
        )

        assign_url = f"https://moodle.astanait.edu.kz/mod/assign/view.php?id={cm_id}"

        diff_time = get_diff_time(assign_due)
        if diff_time < timedelta(days=0):
            return

        if not self.course_state1_assigns:
            self.course_state1_assigns = 1
            self.new_deadlines[self.index_new_assigns] += f"\n\n  [{course_name}]({clear_md(url_to_course)}):"

        self.new_deadlines[self.index_new_assigns] += f"\n      [{clear_md(assign_name)}]({clear_md(assign_url)})"
        self.new_deadlines[self.index_new_assigns] += f"\n      {clear_md(assign_due)}"
        self.new_deadlines[self.index_new_assigns] += f"\n      Remaining: {clear_md(diff_time)}\n"

        if len(self.new_deadlines[self.index_new_assigns]) > 3000:
            self.index_new_assigns += 1
            self.new_deadlines.append("")

    async def set_update_remind_assing(self, assign: dict[str, Any], course: Course, submitted_dict: dict[str, bool]):
        course_name = clear_md(course.name)
        url_to_course = f"/course/view.php?id={course.course_id}"

        assign_id = str(assign["id"])
        cm_id = str(assign["cmid"])
        assign_name = assign["name"]
        assign_due = (datetime.utcfromtimestamp(assign["duedate"]) + timedelta(hours=5)).strftime(
            "%A, %d %B %Y, %I:%M %p"
        )
        assignment_graded = bool(int(assign["grade"]))

        submitted = submitted_dict[assign_id]

        assign_url = f"https://moodle.astanait.edu.kz/mod/assign/view.php?id={cm_id}"

        if cm_id not in course.deadlines:
            if not submitted:
                self.notify_new_deadline(course=course, assign=assign)

            DeadlineDB.set_deadline(
                user_id=self.user.user_id,
                course_id=course.course_id,
                deadline_id=int(cm_id),
                assign_id=int(assign_id),
                name=assign_name,
                due=datetime.strptime(assign_due, "%A, %d %B %Y, %I:%M %p"),
                graded=assignment_graded,
                submitted=submitted,
                status={"status03": 0, "status1": 0, "status2": 0, "status3": 0},
            )
            return

        deadline: Deadline = course.deadlines[cm_id]
        deadline.assign_id = assign_id
        diff_time = get_diff_time(assign_due)
        deadline.graded = assignment_graded
        deadline.submitted = submitted
        old_status = deepcopy(deadline.status)

        if not submitted:
            if assign_due != deadline.due.strftime("%A, %d %B %Y, %I:%M %p"):
                if not self.course_state2_assigns:
                    self.course_state2_assigns = 1
                    self.updated_deadlines[
                        self.index_updated_assigns
                    ] += f"\n\n  [{course_name}]({clear_md(url_to_course)}):"

                self.updated_deadlines[
                    self.index_updated_assigns
                ] += f"\n      [{clear_md(deadline.name)}]({clear_md(assign_url)})"
                self.updated_deadlines[self.index_updated_assigns] += f"\n      {clear_md(assign_due)}"
                self.updated_deadlines[self.index_updated_assigns] += f"\n      Remaining: {clear_md(diff_time)}\n"

                if len(self.updated_deadlines[self.index_updated_assigns]) > 3000:
                    self.index_updated_assigns += 1
                    self.updated_deadlines.append("")

            reminders_filter = [
                ["status03", timedelta(hours=3)],
                ["status1", timedelta(days=1)],
                ["status2", timedelta(days=2)],
                ["status3", timedelta(days=3)],
            ]

            for i, _ in enumerate(reminders_filter):
                key, td = reminders_filter[i]
                if deadline.status.get(key, 0) or diff_time > timedelta(hours=1) or diff_time < td:
                    continue

                if not self.course_state3_assigns:
                    self.course_state3_assigns = 1
                    self.upcoming_deadlines[
                        self.index_upcoming_assigns
                    ] += f"\n\n  [{course_name}]({clear_md(url_to_course)}):"

                self.upcoming_deadlines[
                    self.index_upcoming_assigns
                ] += f"\n      [{clear_md(deadline.name)}]({clear_md(assign_url)})"
                self.upcoming_deadlines[self.index_upcoming_assigns] += f"\n      {clear_md(assign_due)}"
                self.upcoming_deadlines[self.index_upcoming_assigns] += f"\n      Remaining: {clear_md(diff_time)}\n"

                if len(self.upcoming_deadlines[self.index_upcoming_assigns]) > 3000:
                    self.index_upcoming_assigns += 1
                    self.upcoming_deadlines.append("")

                for _ in range(i, 4):
                    key, td = reminders_filter[_]
                    deadline.status[key] = 1
                    break

        if (
            assign_due == deadline.due.strftime("%A, %d %B %Y, %I:%M %p")
            and old_status == deadline.status
            and deadline.submitted == submitted
        ):
            return

        DeadlineDB.update_deadline(
            user_id=self.user.user_id,
            deadline_id=int(cm_id),
            name=assign_name,
            due=datetime.strptime(assign_due, "%A, %d %B %Y, %I:%M %p"),
            graded=assignment_graded,
            submitted=submitted,
            status=deadline.status,
        )

    async def set_assigns(self, courses_assigns):
        self.updated_deadlines = ["Updated deadlines:"]
        self.new_deadlines = ["New deadlines:"]
        self.upcoming_deadlines = ["Upcoming deadlines:"]

        self.index_updated_assigns = 0
        self.index_new_assigns = 0
        self.index_upcoming_assigns = 0

        for course_assigns in [cs for cs in courses_assigns if self.user.courses[str(cs["id"])].active]:
            self.course_state1_assigns = 0
            self.course_state2_assigns = 0
            self.course_state3_assigns = 0

            course = self.user.courses[str(course_assigns["id"])]

            assignment_ids_to_check = [str(assign["id"]) for assign in course_assigns["assignments"]]

            check_tasks = [self.is_assignment_submitted(assign_id) for assign_id in assignment_ids_to_check]
            results = await asyncio.gather(*check_tasks)
            submitted_dict = {id: submitted for submitted, id in results}

            for assign in course_assigns["assignments"]:
                await self.set_update_remind_assing(assign=assign, course=course, submitted_dict=submitted_dict)

    async def set_gpa(self, gpa):
        avg_gpa = gpa["averageGpa"]
        # all_credits_sum = gpa["allCreditsSum"]
        gpa_dict = {}
        for key, val in gpa["gpaOfTrimesters"].items():
            if key == "0":
                gpa_dict["Summer Trimester GPA"] = val
            else:
                gpa_dict[f"Trimester {key} GPA"] = val
        gpa_dict["Average performance GPA"] = avg_gpa

        self.user.gpa = gpa_dict

    async def set_curriculum(self, curriculum):
        self.user.curriculum = {
            "1": {"1": {}, "2": {}, "3": {}},
            "2": {"1": {}, "2": {}, "3": {}},
            "3": {"1": {}, "2": {}, "3": {}},
        }
        for component in curriculum:
            component_id = str(component["id"])
            year = str(component["curriculum"]["year"])
            trimester = str(component["curriculum"]["numberOfTrimester"])
            discipline = {
                "id": component_id,
                "name": component["curriculum"]["discipline"]["titleEn"],
                "credits": component["curriculum"]["discipline"]["volumeCredits"],
            }
            self.user.curriculum[year][trimester][component_id] = discipline

    async def get_gpa(self):
        headers = {
            "Authorization": f"Bearer {self.user.token_du}",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Origin": "https://du.astanait.edu.kz",
            "Referer": "https://du.astanait.edu.kz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
        }
        return await self.make_request(
            headers=headers,
            is_du=True,
            host="https://du.astanait.edu.kz:8765",
            end_point="/astanait-office-module/api/v1/academic-department/assessment-report/transcript-gpa-for-student",
        )

    async def get_curriculum(self, course_num: int):
        headers = {
            "Authorization": f"Bearer {self.user.token_du}",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Origin": "https://du.astanait.edu.kz",
            "Referer": "https://du.astanait.edu.kz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
        }

        params = {"course": course_num}
        return await self.make_request(
            headers=headers,
            params=params,
            is_du=True,
            host="https://du.astanait.edu.kz:8765",
            end_point="/astanait-office-module/api/v1/student-discipline-choose/get-student-IC-by-course-for-student",
        )
