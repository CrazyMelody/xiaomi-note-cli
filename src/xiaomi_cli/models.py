"""Data models and enums for Xiaomi Notes / Todo."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class ReminderType(IntEnum):
    """Reminder type values used by Xiaomi Todo."""

    NO_SET = 0
    DATE = 1
    ACCURATE_TIME = 2


class ReminderRepeatType(IntEnum):
    """Repeat type values used by Xiaomi Todo."""

    NOT_REPEAT = 0
    EVERY_DAY = 1
    EVERY_WEEK = 2
    WEEKDAY = 3
    EVERY_MONTH = 7
    EVERY_YEAR = 8


class TodoListType(IntEnum):
    """Todo content type values used by Xiaomi Todo."""

    COMMON = 0
    HAS_SON = 1


class TodoItemState(IntEnum):
    """Finished state values used by Xiaomi Todo."""

    NO = 0
    YES = 1


class TodoInputType(IntEnum):
    """Todo input source type values used by Xiaomi Todo."""

    CUSTOM = 0
    AUDIO = 1


class XiaomiResponse(BaseModel):
    """Generic Xiaomi API response wrapper."""

    result: str | None = None
    retriable: bool | None = None
    code: int | None = None
    description: str | None = None
    data: Any = None
    ts: int | None = None


class NoteEntry(BaseModel):
    """Subset of Xiaomi note entry fields used by the CLI."""

    id: str
    tag: str | int | None = None
    type: str | None = None
    subject: str | None = None
    snippet: str | None = None
    content: str | None = None
    folderId: str | int | None = None
    colorId: int | None = None
    alertDate: int | None = None
    createDate: int | None = None
    modifyDate: int | None = None
    status: str | None = None
    extraInfo: str | None = None
    setting: dict[str, Any] | None = None
    encryptInfo: Any = None


class TodoSubEntity(BaseModel):
    """Sub item in a checklist-style todo."""

    content: str
    isFinish: bool = False


class TodoComplexContent(BaseModel):
    """Structured todo content for checklist-style items."""

    title: str
    subTodoEntities: list[TodoSubEntity] = Field(default_factory=list)
    isExpand: bool = True


class TodoEntity(BaseModel):
    """Flattened Xiaomi todo entity."""

    id: int | str
    syncId: int | str
    content: str
    plainText: str
    listType: int
    createTime: int
    lastModifiedTime: int
    customSortId: int = 0
    remindType: int = ReminderType.NO_SET
    remindRepeatType: int = ReminderRepeatType.NOT_REPEAT
    remindTime: int = 0
    firstRemindTime: int = 0
    expireTime: int = 0
    isFinish: int = TodoItemState.NO
    markFinishTime: int = 0
    inputType: int = TodoInputType.CUSTOM
    audioFileField: str = ""
    audioFileName: str = ""
    audioFileSize: int = 0
    colorLabel: int = 0
    folderId: int = 0
    hideType: int = 0
    source: int = 0
    localStatus: int = 0
    serverStatus: int = 0
    syncEtag: int | str = 0
    is_finish: bool = False


class TodoRecord(BaseModel):
    """Todo record wrapper returned by Xiaomi Todo APIs."""

    id: str | int
    eTag: str | int
    type: str
    status: str | None = None
    contentJson: dict[str, Any]


class TodoRecordPage(BaseModel):
    """Todo list response data."""

    syncToken: dict[str, Any] | None = None
    records: list[TodoRecord] = Field(default_factory=list)
    hasMore: bool = False


class NotePage(BaseModel):
    """Note list response data."""

    entries: list[NoteEntry] = Field(default_factory=list)
    folders: list[dict[str, Any]] = Field(default_factory=list)
    lastPage: bool | None = None
    syncTag: str | int | None = None
