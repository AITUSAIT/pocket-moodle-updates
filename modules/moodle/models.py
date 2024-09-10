from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MoodleCourse:
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
    progress: float
    completed: bool
    startdate: int
    enddate: int
    marker: int
    lastaccess: int
    isfavourite: bool
    hidden: bool
    overviewfiles: List[str]
    showactivitydates: bool
    showcompletionconditions: Optional[bool]


@dataclass
class Assignment:
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
    intro: str
    introformat: int
    configs: List[dict] = field(default_factory=list)
    introfiles: List[dict] = field(default_factory=list)
    introattachments: List[dict] = field(default_factory=list)


@dataclass
class MoodleCourseWithAssigns:
    id: int
    fullname: str
    shortname: str
    timemodified: int
    assignments: List[Assignment] = field(default_factory=list)


@dataclass
class TableDataItem:
    itemname: "TableDataItemDetail"
    leader: Optional["TableDataItemDetail"]
    weight: Optional["TableDataItemDetail"]
    grade: Optional["TableDataItemDetail"]
    range: Optional["TableDataItemDetail"]
    percentage: Optional["TableDataItemDetail"]
    feedback: Optional["TableDataItemDetail"]
    contributiontocoursetotal: Optional["TableDataItemDetail"]


@dataclass
class TableDataItemDetail:
    content: Optional[str] = None
    colspan: Optional[int] = None
    rowspan: Optional[int] = None
    celltype: Optional[str] = None
    id: Optional[str] = None
    headers: Optional[str] = None


@dataclass
class MoodleGradesTable:
    courseid: int
    userid: int
    userfullname: str
    maxdepth: int
    tabledata: List[TableDataItem]
