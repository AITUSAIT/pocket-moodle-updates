from dataclasses import asdict, dataclass
import json
from datetime import datetime, timedelta
from typing import TypedDict


class UserJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class User:
    user_id: int
    api_token: str
    register_date: datetime
    sub_end_date: datetime | None
    mail: str

    def is_newbie(self) -> bool:
        register_date = self.register_date
        return datetime.now() - register_date < timedelta(days=14)
    
    def is_active_sub(self) -> bool:
        return self.sub_end_date is not None and self.sub_end_date > datetime.now()

    def has_api_token(self) -> bool:
        return self.api_token is not None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), cls=UserJSONEncoder)

    def to_dict(self):
        return json.loads(self.to_json())
    
    def __hash__(self) -> int:
        return hash((self.user_id))

    def __eq__(self, other) -> bool:
        if isinstance(other, User):
            return self.user_id == other.user_id
        return False


@dataclass
class Grade:
    grade_id: int
    name: str
    percentage: str


@dataclass
class Deadline:
    id: int
    assign_id: int
    name: str
    due: datetime
    graded: bool
    submitted: bool
    status: dict


@dataclass
class Course:
    course_id: int
    name: str
    active: bool
    grades: dict[str, Grade]
    deadlines: dict[str, Deadline]


@dataclass
class NotificationStatus:
    status: bool
    is_newbie_requested: bool
    is_update_requested: bool
    is_end_date: bool


@dataclass
class SettingBot:
    status: bool
    notification_grade: bool
    notification_deadline: bool


@dataclass
class SettingApp:
    status: bool
    notification_grade: bool
    notification_deadline: bool


@dataclass
class Server:
    token: str
    name: str
    proxies: list


class Transaction(TypedDict):
    result: int
    message: str
    trackId: int
    payLink: str
    cost: float
    months: int
    user_id: int
    message_id: int
    user_mail: str
