import asyncio
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from dacite import from_dict

from config import TZ
from functions.bot import send
from functions.functions import clear_md, get_diff_time, replace_grade_name
from modules.database import CourseDB, DeadlineDB, GradeDB, NotificationDB
from modules.database.models import Course, Deadline, NotificationStatus
from modules.database.models import User as UserModel
from modules.moodle.models import Assignment, MoodleCourse, MoodleCourseWithAssigns, MoodleGradesTable, TableDataItem

from . import exceptions


@dataclass
class User(UserModel):
    id: int
    courses: dict[str, Course]
    msg: str


class Moodle:
    # pylint: disable=too-many-public-methods
    BASE_URL = "https://moodle.astanait.edu.kz/"

    def __init__(self, user: User, notifications: NotificationStatus) -> None:
        self.user = user
        self.notifications = notifications
        self.user.msg = None

        self.new_grades = ["New grades:"]
        self.updated_grades = ["Updated grades:"]
        self.index_new_grades = 0
        self.index_updated_grades = 0
        self.course_state_new_grades = 0
        self.course_state_updated_grades = 0

        self.new_deadlines = ["New deadlines:"]
        self.updated_deadlines = ["Updated deadlines:"]
        self.upcoming_deadlines = ["Upcoming deadlines:"]
        self.index_new_assigns = 0
        self.index_updated_assigns = 0
        self.index_upcoming_assigns = 0
        self.course_state_new_assigns = 0
        self.course_state_updated_assigns = 0
        self.course_state_upcoming_assigns = 0

        self.grade_id_mapping = {
            "Register Midterm": "0",
            "Register Endterm": "1",
            "Register Term": "2",
            "Register Final": "3",
            "Course total": "4",
        }

    async def __make_request(
        self,
        function: str = None,
        token: str = None,
        params: dict = None,
        headers: dict = None,
        is_du: bool = False,
        host: str = BASE_URL,
        end_point: str = "/webservice/rest/server.php/",
        timeout: int = 5,
    ) -> dict | list | int | str:
        token = token or self.user.api_token
        args = (
            params
            if is_du
            else {"moodlewsrestformat": "json", "wstoken": token, "wsfunction": function, **(params or {})}
        )

        timeout_total = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(host, timeout=timeout_total, headers=headers) as session:
            response = await session.get(end_point, params=args)
            return await response.json()

    async def __handle_token_error(self, message: str):
        if not self.notifications.error_check_token:
            await NotificationDB.set_notification_status(self.user.user_id, "error_check_token", True)
            await send(self.user.user_id, message, True)

    async def __check_api_token(self):
        result = await self.get_users_by_field(self.user.mail, "email")

        if not isinstance(result, list):
            error_code = result.get("errorcode")
            if error_code == "invalidtoken":
                raise exceptions.WrongToken
            if error_code == "invalidparameter":
                raise exceptions.WrongMail

        if len(result) != 1:
            raise exceptions.WrongMail

    async def check(self):
        try:
            await self.__check_api_token()
        except exceptions.WrongToken:
            await self.__handle_token_error("Wrong *Moodle Key*, please try registering again❗️")
            return False
        except exceptions.WrongMail:
            await self.__handle_token_error("*Email* or *Barcode* not valid, please try registering again❗️")
            return False
        except (exceptions.MoodleConnectionFailed, exceptions.TimeoutMoodle, Exception):
            return False
        return True

    async def get_users_by_field(self, value: str, field: str = "email") -> dict:
        return await self.__make_request(
            function="core_user_get_users_by_field", params={"field": field, "values[0]": value}, timeout=10
        )

    async def get_courses(self) -> list[MoodleCourse]:
        if not self.user.id:
            self.user.id = (await self.get_users_by_field(self.user.mail))[0]["id"]
        result: list[dict[str, Any]] = await self.__make_request(
            "core_enrol_get_users_courses", params={"userid": self.user.id}, timeout=10
        )
        return [from_dict(MoodleCourse, course) for course in result]

    async def get_grades(self, courseid: int):
        result = await self.__make_request(
            "gradereport_user_get_grades_table", params={"userid": self.user.id, "courseid": courseid}
        )
        return from_dict(MoodleGradesTable, result["tables"][0])

    async def get_assignments(self) -> list[MoodleCourseWithAssigns]:
        result = await self.__make_request("mod_assign_get_assignments", timeout=10)
        return [from_dict(MoodleCourseWithAssigns, course) for course in result["courses"]]

    async def is_assignment_submitted(self, assign_id: str) -> tuple[bool, str]:
        data = await self.__make_request("mod_assign_get_submission_status", params={"assignid": assign_id})
        status = data.get("lastattempt", {}).get("submission", {}).get("status", None)
        return status == "submitted", assign_id

    async def course_get_contents(self, course_id: int) -> dict[str, Any]:
        return await self.__make_request(function="core_course_get_contents", params={"courseid": course_id})

    async def get_active_courses_ids(self, courses: list[MoodleCourse]) -> list[int]:
        active_courses_ids = []
        now = datetime.now()
        for course in courses:
            end_date = datetime.fromtimestamp(course.enddate)
            if now < end_date:
                active_courses_ids.append(int(course.id))
        return active_courses_ids

    async def add_new_courses(self, courses: list[MoodleCourse], active_courses_ids: list[int]):
        for course in courses:
            course_id = str(course.id)
            active = int(course_id) in active_courses_ids

            if course_id not in self.user.courses:
                CourseDB.set_course(self.user.user_id, int(course_id), course.shortname, active)
            else:
                if self.user.courses[course_id].active != active:
                    CourseDB.update_course_user_pair(self.user.user_id, int(course_id), active)
        await CourseDB.commit()

    async def set_grades(self, courses_grades_table: list[MoodleGradesTable], course_ids: list[int]):
        for grade_table in self.filter_courses_by_ids(courses_grades_table, course_ids):
            self.course_state_new_grades = 0
            self.course_state_updated_grades = 0
            course = self.user.courses[str(grade_table.courseid)]
            url_to_course = f"{self.BASE_URL}/grade/report/user/index.php?id={course.course_id}"
            await self.process_grades(grade_table, course, url_to_course)

    def filter_courses_by_ids(
        self, courses_grades_table: list[MoodleGradesTable], course_ids: list[int]
    ) -> list[MoodleGradesTable]:
        return [grade_table for grade_table in courses_grades_table if grade_table.courseid in course_ids]

    async def process_grades(self, grades_table: MoodleGradesTable, course: Course, url_to_course: str):
        for grade in grades_table.tabledata:
            if not grade.percentage:
                continue
            if not grade.percentage.content:
                continue

            name, grade_id, percentage = self.extract_grade_details(grade)
            await self.update_or_create_grade(course, grade_id, name, percentage, url_to_course)

    def extract_grade_details(self, grade: TableDataItem) -> tuple[str, str, str]:
        name = replace_grade_name(BeautifulSoup(grade.itemname.content, "lxml").text)
        grade_id = str(grade.itemname.id.split("_")[1])
        if name in self.grade_id_mapping:
            grade_id = self.grade_id_mapping[name]
        percentage = grade.percentage.content.replace(",", ".")
        return name, grade_id, percentage

    async def update_or_create_grade(
        self, course: Course, grade_id: str, name: str, percentage: str, url_to_course: str
    ):
        if grade_id not in course.grades:
            await self.add_new_grade(course, grade_id, name, percentage, url_to_course)
        elif str(percentage) != str(course.grades[grade_id].percentage):
            await self.update_existing_grade(course, grade_id, name, percentage, url_to_course)

    async def add_new_grade(self, course: Course, grade_id: str, name: str, percentage: str, url_to_course: str):
        if "%" in percentage:
            if not self.course_state_new_grades:
                self.course_state_new_grades = 1
                self.new_grades[self.index_new_grades] += f"\n\n  [{clear_md(course.name)}]({clear_md(url_to_course)}):"

            self.append_grade(self.new_grades, name, clear_md(percentage))
            await GradeDB.set_grade(
                user_id=self.user.user_id,
                course_id=course.course_id,
                grade_id=int(grade_id),
                name=name,
                percentage=percentage,
            )

    async def update_existing_grade(self, course: Course, grade_id: str, name: str, percentage: str, url_to_course: str):
        old_grade = course.grades[grade_id].percentage
        if percentage != "Error" and not (percentage == "-" and old_grade == "Error"):
            if not self.course_state_updated_grades:
                self.course_state_updated_grades = 1
                self.updated_grades[
                    self.index_updated_grades
                ] += f"\n\n  [{clear_md(course.name)}]({clear_md(url_to_course)}):"

            self.append_grade(self.updated_grades, name, f"{clear_md(old_grade)} \-\> *{clear_md(percentage)}*")
            await GradeDB.update_grade(
                user_id=self.user.user_id, course_id=course.course_id, grade_id=int(grade_id), percentage=percentage
            )

    def append_grade(self, grade_list: list[str], name: str, percentage: str):
        grade_list[self.index_new_grades] += f"\n      {clear_md(name)}\: {percentage}"
        if len(grade_list[self.index_new_grades]) > 3000:
            self.index_new_grades += 1
            grade_list.append("")

    def notify_new_deadline(self, course: Course, assign: Assignment):
        course_name, assign_name, assign_due, assign_url = self.get_assign_details(course, assign)
        diff_time = get_diff_time(assign_due)

        if diff_time < timedelta(days=0):
            return

        self.append_new_deadline(course_name, assign_name, assign_due, assign_url, diff_time)

    def get_assign_details(self, course: Course, assign: Assignment) -> tuple[str, str, str, str]:
        assign_due = datetime.fromtimestamp(assign.duedate).strftime("%A, %d %B %Y, %I:%M %p")
        assign_url = f"{self.BASE_URL}/mod/assign/view.php?id={assign.cmid}"
        return course.name, assign.name, assign_due, assign_url

    def append_new_deadline(
        self, course_name: str, assign_name: str, assign_due: str, assign_url: str, diff_time: timedelta
    ):
        if not self.course_state_new_assigns:
            self.course_state_new_assigns = 1
            self.new_deadlines[self.index_new_assigns] += f"\n\n  [{clear_md(course_name)}]({clear_md(assign_url)}):"

        self.new_deadlines[self.index_new_assigns] += f"\n      [{clear_md(assign_name)}]({clear_md(assign_url)})"
        self.new_deadlines[self.index_new_assigns] += f"\n      {clear_md(assign_due)}"
        self.new_deadlines[self.index_new_assigns] += f"\n      Remaining: {clear_md(diff_time)}\n"

        if len(self.new_deadlines[self.index_new_assigns]) > 3000:
            self.index_new_assigns += 1
            self.new_deadlines.append("")

    async def set_update_remind_assign(self, assign: Assignment, course: Course, submitted_dict: dict[str, bool]):
        assignment_graded = bool(int(assign.grade))
        submitted = submitted_dict[str(assign.id)]
        cm_id = str(assign.cmid)

        if cm_id not in course.deadlines:
            if not submitted:
                self.notify_new_deadline(course, assign)
            await self.save_new_deadline(course, assign, submitted, assignment_graded)
        else:
            await self.update_existing_deadline(course, assign, submitted, assignment_graded)

    async def save_new_deadline(self, course: Course, assign: Assignment, submitted: bool, assignment_graded: bool):
        DeadlineDB.set_deadline(
            user_id=self.user.user_id,
            course_id=course.course_id,
            deadline_id=int(assign.cmid),
            assign_id=int(assign.id),
            name=assign.name,
            due=datetime.fromtimestamp(assign.duedate),
            graded=assignment_graded,
            submitted=submitted,
            status={"status03": 0, "status1": 0, "status2": 0, "status3": 0},
        )

    def append_updated_deadline(
        self, course_name: str, assign_name: str, assign_due: str, assign_url: str, diff_time: timedelta
    ):
        if not self.course_state_updated_assigns:
            self.course_state_updated_assigns = 1
            self.updated_deadlines[
                self.index_updated_assigns
            ] += f"\n\n  [{clear_md(course_name)}]({clear_md(assign_url)}):"

        self.updated_deadlines[
            self.index_updated_assigns
        ] += f"\n      [{clear_md(assign_name)}]({clear_md(assign_url)})"
        self.updated_deadlines[self.index_updated_assigns] += f"\n      {clear_md(assign_due)}"
        self.updated_deadlines[self.index_updated_assigns] += f"\n      Remaining: {clear_md(diff_time)}\n"

        if len(self.updated_deadlines[self.index_updated_assigns]) > 3000:
            self.index_updated_assigns += 1
            self.updated_deadlines.append("")

    async def update_existing_deadline(
        self, course: Course, assign: Assignment, submitted: bool, assignment_graded: bool
    ):
        course_name, assign_name, assign_due, assign_url = self.get_assign_details(course, assign)
        deadline = course.deadlines[str(assign.cmid)]
        diff_time = get_diff_time(datetime.fromtimestamp(assign.duedate).strftime("%A, %d %B %Y, %I:%M %p"))
        old_status = deepcopy(deadline.status)
        await self.check_reminders(deadline, diff_time, course, assign)
        if (
            assign.duedate == deadline.due.timestamp()
            and old_status == deadline.status
            and deadline.submitted == submitted
        ):
            return
        self.append_updated_deadline(course_name, assign_name, assign_due, assign_url, diff_time)
        DeadlineDB.update_deadline(
            user_id=self.user.user_id,
            deadline_id=int(assign.cmid),
            name=assign.name,
            due=datetime.fromtimestamp(assign.duedate),
            graded=assignment_graded,
            submitted=submitted,
            status=deadline.status,
        )

    async def set_assigns(self, courses_assigns: list[MoodleCourseWithAssigns]):
        for course_assigns in self.filter_active_courses_assigns(courses_assigns):
            self.course_state_new_assigns = 0
            self.course_state_updated_assigns = 0
            self.course_state_upcoming_assigns = 0
            await self.process_course_assignments(course_assigns)

    def filter_active_courses_assigns(
        self, courses_assigns: list[MoodleCourseWithAssigns]
    ) -> list[MoodleCourseWithAssigns]:
        return [cs for cs in courses_assigns if self.user.courses[str(cs.id)].active]

    async def process_course_assignments(self, course_assigns: MoodleCourseWithAssigns):
        course = self.user.courses[str(course_assigns.id)]
        assignment_ids_to_check = [str(assign.id) for assign in course_assigns.assignments]
        submitted_dict: dict[str, bool] = await self.check_assignments_submissions(assignment_ids_to_check)
        for assign in course_assigns.assignments:
            await self.set_update_remind_assign(assign, course, submitted_dict)

    async def check_assignments_submissions(self, assignment_ids: list[str]) -> dict[str, bool]:
        tasks = [self.is_assignment_submitted(assign_id) for assign_id in assignment_ids]
        results = await asyncio.gather(*tasks)
        return {id: submitted for submitted, id in results}

    async def check_reminders(self, deadline: Deadline, diff_time: timedelta, course: Course, assign: Assignment):
        """
        Check for reminders based on the remaining time (diff_time) for the assignment.
        Update the deadline's status to trigger reminders accordingly.
        """
        course_name, assign_name, assign_due, assign_url = self.get_assign_details(course, assign)

        # Check the time difference and send reminders
        if diff_time < timedelta(minutes=0):
            return

        if diff_time < timedelta(hours=3):
            # Reminder for less than 3 hours remaining
            if not deadline.status["status03"]:
                deadline.status["status03"] = 1
                self.append_deadline_reminder(course_name, assign_name, assign_due, assign_url, diff_time)
        elif diff_time < timedelta(days=1):
            # Reminder for less than 1 day remaining
            if not deadline.status["status1"]:
                deadline.status["status1"] = 1
                self.append_deadline_reminder(course_name, assign_name, assign_due, assign_url, diff_time)
        elif diff_time < timedelta(days=2):
            # Reminder for less than 2 days remaining
            if not deadline.status["status2"]:
                deadline.status["status2"] = 1
                self.append_deadline_reminder(course_name, assign_name, assign_due, assign_url, diff_time)
        elif diff_time < timedelta(days=3):
            # Reminder for less than 3 days remaining
            if not deadline.status["status3"]:
                deadline.status["status3"] = 1
                self.append_deadline_reminder(course_name, assign_name, assign_due, assign_url, diff_time)

    def append_deadline_reminder(self, course_name, assign_name, assign_due, assign_url, diff_time):
        """
        Append a reminder for the assignment deadline based on the remaining time description.
        """
        if not self.course_state_upcoming_assigns:
            self.course_state_upcoming_assigns = 1
            self.upcoming_deadlines[
                self.index_upcoming_assigns
            ] += f"\n\n  [{clear_md(course_name)}]({clear_md(assign_url)}):"

        self.upcoming_deadlines[self.index_upcoming_assigns] += (
            f"\n      {clear_md(assign_name)}"
            f"\n      {clear_md(assign_due)}"
            f"\n      Remaining: {clear_md(diff_time)}\n"
            "\n"
        )

        if len(self.upcoming_deadlines[self.index_upcoming_assigns]) > 3000:
            self.index_upcoming_assigns += 1
            self.upcoming_deadlines.append("")
