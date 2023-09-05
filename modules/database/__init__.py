from . import models
from .db import DB
from .user import UserDB
from .deadline import DeadlineDB 
from .grade import GradeDB 
from .course import CourseDB
from .notification import NotificationDB
from .payment import PaymentDB
from .server import ServerDB
from .settings_bot import SettingsBotDB

__all__ = [
    'DB',
    'UserDB',
    'CourseDB',
    'GradeDB',
    'DeadlineDB',
    'NotificationDB',
    'SettingsBotDB',
    'ServerDB',
    'PaymentDB',
    'models',
]


