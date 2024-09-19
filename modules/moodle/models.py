from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class MoodleCourse(PydanticBaseModel):
    id: int
    shortname: str
    fullname: str
    displayname: str
    enrolledusercount: int
    idnumber: str
    visible: int
    summary: str
    summaryformat: int
    format: str
    showgrades: bool
    lang: str
    enablecompletion: bool
    completionhascriteria: bool
    completionusertracked: bool
    category: int
    startdate: int
    enddate: int
    marker: int
    isfavourite: bool
    hidden: bool
    overviewfiles: List[str | dict]
    showactivitydates: bool
    showcompletionconditions: Optional[bool]
    progress: Optional[float]
    completed: Optional[bool]
    lastaccess: Optional[int]


class MoodleAssignment(PydanticBaseModel):
    id: int
    cmid: int
    course: int
    name: str
    nosubmissions: int
    submissiondrafts: int
    sendnotifications: int
    sendlatenotifications: int
    sendstudentnotifications: int
    duedate: int
    allowsubmissionsfromdate: int
    grade: int
    timemodified: int
    completionsubmit: int
    cutoffdate: int
    gradingduedate: int
    teamsubmission: int
    requireallteammemberssubmit: int
    teamsubmissiongroupingid: int
    blindmarking: int
    hidegrader: int
    revealidentities: int
    attemptreopenmethod: str
    maxattempts: int
    markingworkflow: int
    markingallocation: int
    requiresubmissionstatement: int
    preventsubmissionnotingroup: int
    intro: Optional[str]
    introformat: Optional[int]
    configs: List[dict] = Field(default_factory=list)
    introfiles: List[dict] = Field(default_factory=list)
    introattachments: List[dict] = Field(default_factory=list)


class MoodleCourseWithAssigns(PydanticBaseModel):
    id: int
    fullname: str
    shortname: str
    timemodified: int
    assignments: List[MoodleAssignment] = Field(default_factory=list)


class MoodleTableDataItemDetail(PydanticBaseModel):
    content: Optional[str] = None
    colspan: Optional[int] = None
    rowspan: Optional[int] = None
    celltype: Optional[str] = None
    id: Optional[str] = None
    headers: Optional[str] = None


class MoodleTableDataItem(PydanticBaseModel):
    itemname: MoodleTableDataItemDetail
    leader: Optional[MoodleTableDataItemDetail] = None
    weight: Optional[MoodleTableDataItemDetail] = None
    grade: Optional[MoodleTableDataItemDetail] = None
    range: Optional[MoodleTableDataItemDetail] = None
    percentage: Optional[MoodleTableDataItemDetail] = None
    feedback: Optional[MoodleTableDataItemDetail] = None
    contributiontocoursetotal: Optional[MoodleTableDataItemDetail] = None


class MoodleGradesTable(PydanticBaseModel):
    courseid: int
    userid: int
    userfullname: str
    maxdepth: int
    tabledata: List[MoodleTableDataItem | list]


class MoodleCompletionData(PydanticBaseModel):
    state: int
    timecompleted: int
    valueused: bool
    hascompletion: bool
    isautomatic: bool
    istrackeduser: bool
    uservisible: bool
    details: List
    overrideby: Optional[int]


class MoodleDateInfo(PydanticBaseModel):
    label: str
    timestamp: int


class MoodleModuleItem(PydanticBaseModel):
    filename: str
    fileurl: str
    timecreated: int
    timemodified: int
    type: str
    mimetype: Optional[str]
    filesize: Optional[int]


class MoodleModule(PydanticBaseModel):
    id: int
    name: str
    instance: int
    contextid: int
    visible: int
    uservisible: bool
    visibleoncoursepage: int
    modicon: str
    modname: str
    modplural: str
    indent: int
    onclick: str
    customdata: str
    noviewlink: bool
    completion: int
    completiondata: MoodleCompletionData
    dates: List[MoodleDateInfo] = []
    contents: list[MoodleModuleItem] = []
    url: Optional[str] = None
    afterlink: Optional[str] = None
    availabilityinfo: Optional[dict | str] = None
    contentsinfo: Optional[dict] = None


class MoodleContent(PydanticBaseModel):
    id: int
    name: str
    visible: int
    summary: str
    summaryformat: int
    section: int
    hiddenbynumsections: int
    uservisible: bool
    modules: List[MoodleModule]
