from typing import List, Optional

from pydantic import BaseModel, Field


class MoodleCourse(BaseModel):
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
    overviewfiles: List[str]
    showactivitydates: bool
    showcompletionconditions: Optional[bool]
    progress: Optional[float]
    completed: Optional[bool]
    lastaccess: Optional[int]


class Assignment(BaseModel):
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
    configs: List[dict] = Field(default_factory=list)
    introfiles: List[dict] = Field(default_factory=list)
    introattachments: List[dict] = Field(default_factory=list)


class MoodleCourseWithAssigns(BaseModel):
    id: int
    fullname: str
    shortname: str
    timemodified: int
    assignments: List[Assignment] = Field(default_factory=list)


class TableDataItemDetail(BaseModel):
    content: Optional[str] = None
    colspan: Optional[int] = None
    rowspan: Optional[int] = None
    celltype: Optional[str] = None
    id: Optional[str] = None
    headers: Optional[str] = None


class TableDataItem(BaseModel):
    itemname: TableDataItemDetail
    leader: Optional[TableDataItemDetail] = None
    weight: Optional[TableDataItemDetail] = None
    grade: Optional[TableDataItemDetail] = None
    range: Optional[TableDataItemDetail] = None
    percentage: Optional[TableDataItemDetail] = None
    feedback: Optional[TableDataItemDetail] = None
    contributiontocoursetotal: Optional[TableDataItemDetail] = None


class MoodleGradesTable(BaseModel):
    courseid: int
    userid: int
    userfullname: str
    maxdepth: int
    tabledata: List[TableDataItem | list]
