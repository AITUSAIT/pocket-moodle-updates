from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UserJSONEncoder:
    # pylint: disable=no-member
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)  # type: ignore

    # pylint: enable=no-member


class PydanticBaseModel(BaseModel):
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json(self) -> str:
        return self.model_dump_json()

    def to_dict(self, json_support: bool = False) -> Dict[str, Any]:
        return self.model_dump(mode="python" if not json_support else "json")


class User(PydanticBaseModel):
    user_id: int
    api_token: str
    register_date: datetime
    mail: str
    last_active: Optional[datetime]
    is_admin: bool
    is_manager: bool

    def is_newbie(self) -> bool:
        return datetime.now() - self.register_date < timedelta(days=14)

    def is_active_user(self) -> bool:
        return self.last_active is not None and self.last_active > datetime.now() - timedelta(weeks=2)

    def has_api_token(self) -> bool:
        return self.api_token is not None


class MailingModel(PydanticBaseModel):
    id: int
    content: str
    media_type: Optional[str] = None
    media_id: Optional[str] = None


class MailingMessage(PydanticBaseModel):
    id: int
    mailing_id: int
    chat_id: int
    message_id: Optional[int] = None
    sent_date: Optional[datetime] = None
    edit_date: Optional[datetime] = None


class Group(PydanticBaseModel):
    id: int
    tg_id: int
    name: str
    users: List[int]

    class Config:
        frozen = True  # This makes the class hashable


class Grade(PydanticBaseModel):
    grade_id: int
    name: str
    percentage: str

    class Config:
        frozen = True


class Deadline(PydanticBaseModel):
    id: int
    assign_id: int
    name: str
    due: datetime
    graded: bool
    submitted: bool
    status: dict[str, int]

    class Config:
        frozen = False


class Course(PydanticBaseModel):
    course_id: int
    name: str
    active: bool
    grades: Dict[str, Grade]
    deadlines: Dict[str, Deadline]


class GroupedCourse(PydanticBaseModel):
    course_id: int
    name: str
    active: bool
    grades: Dict[str, Grade]
    deadlines: Dict[str, Dict[str, Deadline]]


class NotificationStatus(PydanticBaseModel):
    status: bool
    is_newbie_requested: bool
    is_update_requested: bool
    is_end_date: bool
    error_check_token: bool


class SettingBot(PydanticBaseModel):
    status: bool
    notification_grade: bool
    notification_deadline: bool


class SettingApp(PydanticBaseModel):
    status: bool
    notification_grade: bool
    notification_deadline: bool


class Server(PydanticBaseModel):
    token: str
    name: str
    proxies: List[Any]  # Specify the type if you have more detail on the proxy structure


class CourseContent(PydanticBaseModel):
    id: int
    name: str
    section: int
    modules: Dict[str, "CourseContentModule"]


class CourseContentModule(PydanticBaseModel):
    id: int
    url: str
    name: str
    modplural: str
    modname: str
    files: Dict[str, "CourseContentModuleFile"]
    urls: Dict[str, "CourseContentModuleUrl"]


class CourseContentModuleFile(PydanticBaseModel):
    id: int
    filename: str
    filesize: int
    fileurl: str
    timecreated: int
    timemodified: int
    mimetype: str
    bytes: bytes


class CourseContentModuleUrl(PydanticBaseModel):
    id: int
    name: str
    url: str
