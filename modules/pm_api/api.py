import aiohttp

from config import PM_HOST
from modules.pm_api.course_contents import CourseContentsAPI
from modules.pm_api.courses import CoursesAPI
from modules.pm_api.deadlines import DeadlinesAPI
from modules.pm_api.grades import GradesAPI
from modules.pm_api.groups import GroupsAPI
from modules.pm_api.notifications import NotificationsAPI
from modules.pm_api.queue import QueueAPI
from modules.pm_api.settings import SettingsAPI
from modules.pm_api.users import UsersAPI


class PocketMoodleAPI(
    UsersAPI, GroupsAPI, CoursesAPI, GradesAPI, DeadlinesAPI, CourseContentsAPI, NotificationsAPI, SettingsAPI, QueueAPI
):  # pylint: disable=too-many-ancestors
    host = PM_HOST
    timeout = aiohttp.ClientTimeout(10.0)
