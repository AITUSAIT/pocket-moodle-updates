import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp
from bs4 import BeautifulSoup
from line_profiler import profile

from functions.bot import send
from functions.functions import clear_md, get_diff_time, replace_grade_name
from modules.moodle.models import (
    MoodleAssignment,
    MoodleContent,
    MoodleCourse,
    MoodleCourseWithAssigns,
    MoodleGradesTable,
    MoodleTableDataItem,
)
from modules.pm_api.api import PocketMoodleAPI
from modules.pm_api.models import Course, Deadline, Grade, NotificationStatus, User

from . import exceptions


class ExtendedUser(User):
    courses: dict[str, Course]
    moodle_id: Optional[int]
    msg: Optional[str]


class Moodle:
    # pylint: disable=too-many-public-methods
    BASE_URL = "https://moodle.astanait.edu.kz/"

    def __init__(self, user: ExtendedUser, notification_status: NotificationStatus) -> None:
        self.user: ExtendedUser = user
        self.grades: dict[str, Grade] = {}
        self.deadlines: dict[str, Deadline] = {}
        self.user.msg = None
        self.notification_status = notification_status

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
        function: str | None = None,
        token: str | None = None,
        params: dict | None = None,
        headers: dict[str, Any] | None = None,
        is_du: bool = False,
        host: str = BASE_URL,
        end_point: str = "/webservice/rest/server.php/",
        timeout: int = 5,
    ) -> Any:
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
        if not self.notification_status.error_check_token:
            self.notification_status.error_check_token = True
            await PocketMoodleAPI().set_notification_status(self.user.user_id, self.notification_status)
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

    async def get_users_by_field(self, value: str, field: str = "email") -> list[dict[str, Any]]:
        return await self.__make_request(
            function="core_user_get_users_by_field", params={"field": field, "values[0]": value}, timeout=10
        )

    async def get_courses(self) -> list[MoodleCourse]:
        result: list[dict[str, Any]] = await self.__make_request(
            "core_enrol_get_users_courses", params={"userid": self.user.moodle_id}, timeout=10
        )
        return [MoodleCourse.model_validate(course) for course in result]

    async def get_grades(self, courseid: int):
        result = await self.__make_request(
            "gradereport_user_get_grades_table", params={"userid": self.user.moodle_id, "courseid": courseid}
        )
        return MoodleGradesTable.model_validate(result["tables"][0])

    async def get_assignments(self) -> list[MoodleCourseWithAssigns]:
        result = await self.__make_request("mod_assign_get_assignments", timeout=10)
        return [MoodleCourseWithAssigns.model_validate(course) for course in result["courses"]]

    async def is_assignment_submitted(self, assign_id: str) -> tuple[bool, str]:
        data = await self.__make_request("mod_assign_get_submission_status", params={"assignid": assign_id})
        status = data.get("lastattempt", {}).get("submission", {}).get("status", None)
        return status == "submitted", assign_id

    async def course_get_sections(self, course_id: int) -> list[MoodleContent]:
        json_response = await self.__make_request(function="core_course_get_contents", params={"courseid": course_id})
        return [MoodleContent.model_validate(data) for data in json_response]

    async def get_active_courses_ids(self, courses: list[MoodleCourse]) -> list[int]:
        active_courses_ids = []
        now = datetime.now()
        for course in courses:
            end_date = datetime.fromtimestamp(course.enddate)
            if now < end_date:
                active_courses_ids.append(int(course.id))
        return active_courses_ids

    async def add_new_courses(self, moodle_courses: list[MoodleCourse], active_courses_ids: list[int]):
        for moodle_course in moodle_courses:
            course_id = str(moodle_course.id)
            active = int(course_id) in active_courses_ids

            course = Course(
                course_id=moodle_course.id,
                name=moodle_course.shortname,
                active=active,
            )
            if course_id not in self.user.courses:
                await PocketMoodleAPI().link_user_with_course(self.user.user_id, course)
            else:
                if self.user.courses[course_id].active != active:
                    await PocketMoodleAPI().update_user_link_with_course(self.user.user_id, course)
            self.user.courses[course_id] = course

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
        self.grades = await PocketMoodleAPI().get_grades(self.user.user_id, course.course_id)
        for moodle_grade in grades_table.tabledata:
            if isinstance(moodle_grade, list):
                continue
            if not moodle_grade.percentage:
                continue
            if not moodle_grade.percentage.content:
                continue

            grade = self.extract_grade_details(moodle_grade)
            if not grade:
                return

            await self.update_or_create_grade(course, grade, url_to_course)

    def extract_grade_details(self, grade: MoodleTableDataItem) -> None | Grade:
        name = replace_grade_name(BeautifulSoup(grade.itemname.content, "lxml").text)
        if not grade.itemname.id or not grade.percentage or not grade.percentage.content:
            return None

        grade_id = str(grade.itemname.id.split("_")[1])
        if name in self.grade_id_mapping:
            grade_id = self.grade_id_mapping[name]
        percentage = grade.percentage.content.replace(",", ".")

        return Grade(grade_id=int(grade_id), name=name, percentage=percentage)

    async def update_or_create_grade(self, course: Course, grade: Grade, url_to_course: str):
        if str(grade.grade_id) not in self.grades:
            await self.add_new_grade(course, grade, url_to_course)
        elif str(grade.percentage) != str(self.grades[str(grade.grade_id)].percentage):
            await self.update_existing_grade(course, grade, url_to_course)

    async def add_new_grade(self, course: Course, grade: Grade, url_to_course: str):
        if grade.percentage == "-":
            return

        if not self.course_state_new_grades:
            if len(self.new_grades[self.index_new_grades]) > 2000:
                self.index_new_grades += 1
                self.new_grades.append("")

            self.course_state_new_grades = 1
            self.new_grades[self.index_new_grades] += f"\n\n  [{clear_md(course.name)}]({clear_md(url_to_course)}):"

        self.append_new_grade(grade.name, clear_md(grade.percentage))
        asyncio.create_task(
            PocketMoodleAPI().link_user_with_grade(user_id=self.user.user_id, course=course, grade=grade)
        )

    async def update_existing_grade(self, course: Course, grade: Grade, url_to_course: str):
        old_grade = self.grades[str(grade.grade_id)].percentage
        if grade.percentage == "Error" or (grade.percentage == "-" and old_grade == "Error"):
            return

        if not self.course_state_updated_grades:
            if len(self.updated_grades[self.index_updated_grades]) > 2000:
                self.index_updated_grades += 1
                self.updated_grades.append("")

            self.course_state_updated_grades = 1
            self.updated_grades[
                self.index_updated_grades
            ] += f"\n\n  [{clear_md(course.name)}]({clear_md(url_to_course)}):"

        self.append_updated_grade(grade.name, f"{clear_md(old_grade)} \-\> *{clear_md(grade.percentage)}*")
        asyncio.create_task(
            PocketMoodleAPI().update_user_link_with_grade(user_id=self.user.user_id, course=course, grade=grade)
        )

    def append_updated_grade(self, name: str, percentage: str):
        self.updated_grades[self.index_updated_grades] += f"\n      {clear_md(name)}\: {percentage}"

    def append_new_grade(self, name: str, percentage: str):
        self.new_grades[self.index_new_grades] += f"\n      {clear_md(name)}\: {percentage}"

    def notify_new_deadline(self, course: Course, assign: MoodleAssignment):
        course_name, assign_name, assign_due, assign_url = self.get_assign_details(course, assign)
        diff_time = get_diff_time(assign_due)

        if diff_time < timedelta(days=0):
            return

        self.append_new_deadline(course_name, assign_name, assign_due, assign_url, diff_time)

    def get_assign_details(self, course: Course, assign: MoodleAssignment) -> tuple[str, str, str, str]:
        assign_due = datetime.fromtimestamp(assign.duedate).strftime("%A, %d %B %Y, %I:%M %p")
        assign_url = f"{self.BASE_URL}/mod/assign/view.php?id={assign.cmid}"
        return course.name, assign.name, assign_due, assign_url

    def append_new_deadline(
        self, course_name: str, assign_name: str, assign_due: str, assign_url: str, diff_time: timedelta
    ):
        if not self.course_state_new_assigns:
            if len(self.new_deadlines[self.index_new_assigns]) > 2000:
                self.index_new_assigns += 1
                self.new_deadlines.append("")
            self.course_state_new_assigns = 1
            self.new_deadlines[self.index_new_assigns] += f"\n\n  [{clear_md(course_name)}]({clear_md(assign_url)}):"

        self.new_deadlines[self.index_new_assigns] += (
            f"\n      [{clear_md(assign_name)}]({clear_md(assign_url)})"
            f"\n      {clear_md(assign_due)}"
            f"\n      Remaining: {clear_md(diff_time)}\n"
        )

    async def set_update_remind_assign(self, assign: MoodleAssignment, course: Course, submitted_dict: dict[str, bool]):
        submitted = submitted_dict[str(assign.id)]
        cm_id = str(assign.cmid)

        deadline = Deadline(
            id=assign.cmid,
            assign_id=assign.id,
            name=assign.name,
            due=datetime.fromtimestamp(assign.duedate),
            graded=bool(int(assign.grade)),
            submitted=submitted_dict[str(assign.id)],
            status={"status03": 0, "status1": 0, "status2": 0, "status3": 0},
        )
        if cm_id not in self.deadlines:
            if not submitted:
                self.notify_new_deadline(course, assign)
            await self.save_new_deadline(course, deadline)
        else:
            await self.update_existing_deadline(course, assign, submitted)

    async def save_new_deadline(
        self,
        course: Course,
        deadline: Deadline,
    ):
        asyncio.create_task(
            PocketMoodleAPI().link_user_with_deadline(user_id=self.user.user_id, course=course, deadline=deadline)
        )

    def append_updated_deadline(
        self, course_name: str, assign_name: str, assign_due: str, assign_url: str, diff_time: timedelta
    ):
        if not self.course_state_updated_assigns:
            if len(self.updated_deadlines[self.index_updated_assigns]) > 2000:
                self.index_updated_assigns += 1
                self.updated_deadlines.append("")
            self.course_state_updated_assigns = 1
            self.updated_deadlines[
                self.index_updated_assigns
            ] += f"\n\n  [{clear_md(course_name)}]({clear_md(assign_url)}):"

        self.updated_deadlines[self.index_updated_assigns] += (
            f"\n      [{clear_md(assign_name)}]({clear_md(assign_url)})"
            f"\n      {clear_md(assign_due)}"
            f"\n      Remaining: {clear_md(diff_time)}\n"
        )

    async def update_existing_deadline(self, course: Course, assign: MoodleAssignment, submitted: bool):
        course_name, assign_name, assign_due, assign_url = self.get_assign_details(course, assign)
        deadline = self.deadlines[str(assign.cmid)]
        diff_time = get_diff_time(datetime.fromtimestamp(assign.duedate).strftime("%A, %d %B %Y, %I:%M %p"))
        old_status = deepcopy(deadline.status)
        await self.check_reminders(deadline, diff_time, course, assign)

        if assign.duedate != deadline.due.timestamp() or deadline.submitted != submitted:
            self.append_updated_deadline(course_name, assign_name, assign_due, assign_url, diff_time)

            deadline.submitted = submitted
            deadline.due = datetime.fromtimestamp(assign.duedate)
            asyncio.create_task(
                PocketMoodleAPI().update_user_link_with_deadline(
                    user_id=self.user.user_id, course=course, deadline=deadline
                )
            )
        elif old_status != deadline.status:
            asyncio.create_task(
                PocketMoodleAPI().update_user_link_with_deadline(
                    user_id=self.user.user_id, course=course, deadline=deadline
                )
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
        self.deadlines = await PocketMoodleAPI().get_deadlines(self.user.user_id, course.course_id)
        assignment_ids_to_check = [str(assign.id) for assign in course_assigns.assignments]
        submitted_dict: dict[str, bool] = await self.check_assignments_submissions(assignment_ids_to_check)
        for assign in course_assigns.assignments:
            await self.set_update_remind_assign(assign, course, submitted_dict)

    async def check_assignments_submissions(self, assignment_ids: list[str]) -> dict[str, bool]:
        tasks = [self.is_assignment_submitted(assign_id) for assign_id in assignment_ids]
        results = await asyncio.gather(*tasks)
        return {id: submitted for submitted, id in results}

    async def check_reminders(self, deadline: Deadline, diff_time: timedelta, course: Course, assign: MoodleAssignment):
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
            f"\n      Remaining: {clear_md(diff_time)}"
            "\n"
        )

        if len(self.upcoming_deadlines[self.index_upcoming_assigns]) > 2000:
            self.index_upcoming_assigns += 1
            self.upcoming_deadlines.append("")
