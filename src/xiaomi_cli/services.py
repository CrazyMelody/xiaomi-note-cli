"""High-level services for Xiaomi notes and todos."""

from __future__ import annotations

from typing import Any
import json
import time

from .client import XiaomiClient
from .models import (
    ReminderRepeatType,
    ReminderType,
    TodoComplexContent,
    TodoEntity,
    TodoInputType,
    TodoItemState,
    TodoListType,
)


def build_note_create_entry(
    *,
    content: str = "",
    folder_id: str | int = 0,
    color_id: int = 0,
    alert_date: int = 0,
) -> dict[str, Any]:
    """Build the minimal note-create payload used by Xiaomi web app.

    Args:
        content: Initial note content.
        folder_id: Target folder id.
        color_id: Note color id.
        alert_date: Reminder timestamp in milliseconds.

    Returns:
        Minimal create payload accepted by ``POST /note/note``.
    """

    now = int(time.time() * 1000)
    return {
        "content": content,
        "colorId": color_id,
        "folderId": folder_id,
        "alertDate": alert_date,
        "createDate": now,
        "modifyDate": now,
    }


def build_note_update_entry(
    source_entry: dict[str, Any],
    *,
    content: str,
    title: str = "",
    folder_id: str | int | None = None,
    color_id: int | None = None,
    alert_date: int | None = None,
) -> dict[str, Any]:
    """Build a note update payload aligned with Xiaomi web note update requests.

    Args:
        source_entry: Existing note entry returned by the detail API.
        content: Updated note content.
        title: Title stored in ``extraInfo.title``.
        folder_id: Optional folder override.
        color_id: Optional color override.
        alert_date: Optional alert timestamp override.

    Returns:
        Note update payload for ``POST /note/note/{id}``.
    """

    source_extra = source_entry.get("extraInfo")
    try:
        extra_info = json.loads(source_extra) if isinstance(source_extra, str) and source_extra else {}
    except json.JSONDecodeError:
        extra_info = {}
    extra_info["title"] = title
    return {
        "id": str(source_entry["id"]),
        "tag": str(source_entry["tag"]),
        "status": source_entry.get("status", "normal"),
        "createDate": source_entry["createDate"],
        "modifyDate": int(time.time() * 1000),
        "colorId": source_entry.get("colorId", 0) if color_id is None else color_id,
        "content": content,
        "folderId": source_entry.get("folderId", 0) if folder_id is None else folder_id,
        "alertDate": source_entry.get("alertDate", 0) if alert_date is None else alert_date,
        "extraInfo": json.dumps(extra_info, ensure_ascii=False),
    }


def build_todo_record(
    *,
    title: str,
    checklist: list[dict[str, Any]] | None = None,
    remind_at: int | None = None,
    repeat: ReminderRepeatType = ReminderRepeatType.NOT_REPEAT,
    finished: bool = False,
    timestamp_ms: int | None = None,
    record_id: int = 0,
    custom_sort_id: int = 0,
) -> dict[str, Any]:
    """Build a todo create payload that mirrors Xiaomi web app behavior."""

    now = timestamp_ms or int(time.time() * 1000)
    complex_content = TodoComplexContent(
        title=title,
        subTodoEntities=[item if isinstance(item, dict) else {"content": str(item), "isFinish": False} for item in (checklist or [])],
        isExpand=True,
    )
    if complex_content.subTodoEntities:
        content = json.dumps(complex_content.model_dump(), ensure_ascii=False)
        plain_text = "\n".join([title, *[item.content for item in complex_content.subTodoEntities]])
        list_type = TodoListType.HAS_SON
    else:
        content = title
        plain_text = title
        list_type = TodoListType.COMMON

    remind_type = ReminderType.ACCURATE_TIME if remind_at else ReminderType.NO_SET
    first_remind_time = remind_at or 0
    mark_finish_time = now if finished else 0

    entity = TodoEntity(
        id=record_id,
        syncId=-1,
        content=content,
        plainText=plain_text,
        listType=int(list_type),
        createTime=now,
        lastModifiedTime=now,
        customSortId=custom_sort_id,
        remindType=int(remind_type),
        remindRepeatType=int(repeat if remind_at else ReminderRepeatType.NOT_REPEAT),
        remindTime=remind_at or 0,
        firstRemindTime=first_remind_time,
        expireTime=remind_at or 0,
        isFinish=int(TodoItemState.YES if finished else TodoItemState.NO),
        markFinishTime=mark_finish_time,
        inputType=int(TodoInputType.CUSTOM),
        is_finish=False,
    )
    record_content = entity.model_dump()
    record_content["assets"] = []
    return {"type": "entity", "contentJson": record_content}


def build_todo_update_record(
    source_record: dict[str, Any],
    *,
    title: str | None = None,
    checklist: list[dict[str, Any]] | None = None,
    remind_at: int | None = None,
    repeat: ReminderRepeatType | None = None,
    finished: bool | None = None,
    custom_sort_id: int | None = None,
) -> dict[str, Any]:
    """Build a todo update payload by merging changes into an existing record.

    Args:
        source_record: Original todo record returned by Xiaomi APIs.
        title: New title. When omitted, keep the existing title.
        checklist: New checklist. When omitted, keep the existing checklist.
        remind_at: New reminder timestamp. ``None`` means no reminder.
        repeat: New repeat strategy.
        finished: Finished state override.
        custom_sort_id: Optional override for custom sort order.

    Returns:
        Xiaomi-compatible record wrapper ready for ``/update``.
    """

    normalized = normalize_todo_record(source_record)
    content_json = dict(source_record.get("contentJson", {}))
    entity = dict(content_json.get("entity", content_json))
    raw_checklist = normalized["checklist"] if checklist is None else checklist
    next_title = normalized["title"] if title is None else title
    if remind_at:
        next_remind_type = ReminderType.ACCURATE_TIME
        next_remind_time = remind_at
        next_first_remind_time = remind_at
        next_repeat = int(repeat or ReminderRepeatType.NOT_REPEAT)
    else:
        next_remind_type = ReminderType.NO_SET
        next_remind_time = 0
        next_first_remind_time = 0
        next_repeat = int(ReminderRepeatType.NOT_REPEAT)

    if raw_checklist:
        normalized_checklist = [
            item
            if isinstance(item, dict)
            else {"content": str(item), "isFinish": False}
            for item in raw_checklist
        ]
        complex_content = TodoComplexContent(
            title=next_title,
            subTodoEntities=normalized_checklist,
            isExpand=True,
        )
        content = json.dumps(complex_content.model_dump(), ensure_ascii=False)
        plain_text = "\n".join(
            [next_title, *[item["content"] for item in normalized_checklist]]
        )
        list_type = int(TodoListType.HAS_SON)
    else:
        content = next_title
        plain_text = next_title
        list_type = int(TodoListType.COMMON)

    now = int(time.time() * 1000)
    if finished is None:
        is_finish = entity.get("isFinish", int(TodoItemState.NO))
        mark_finish_time = entity.get("markFinishTime", 0)
    elif finished:
        is_finish = int(TodoItemState.YES)
        mark_finish_time = now
        next_repeat = int(ReminderRepeatType.NOT_REPEAT)
    else:
        is_finish = int(TodoItemState.NO)
        mark_finish_time = 0

    updated_entity = {
        **entity,
        "content": content,
        "plainText": plain_text,
        "listType": list_type,
        "lastModifiedTime": now,
        "remindType": int(next_remind_type),
        "remindRepeatType": next_repeat,
        "remindTime": next_remind_time,
        "firstRemindTime": next_first_remind_time,
        "expireTime": next_remind_time if next_remind_time else entity.get("expireTime", 0),
        "isFinish": is_finish,
        "markFinishTime": mark_finish_time,
        "customSortId": entity.get("customSortId", 0)
        if custom_sort_id is None
        else custom_sort_id,
    }
    return {
        "id": source_record.get("id"),
        "eTag": source_record.get("eTag"),
        "type": source_record.get("type", "entity"),
        "contentJson": updated_entity,
    }


def normalize_todo_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten Xiaomi todo record into a CLI-friendly dict."""

    content_json = record.get("contentJson", {})
    entity = content_json.get("entity", content_json)
    content = entity.get("content", "")
    checklist: list[dict[str, Any]] = []
    if entity.get("listType") == int(TodoListType.HAS_SON):
        try:
            parsed = json.loads(content)
            checklist = parsed.get("subTodoEntities", [])
        except json.JSONDecodeError:
            checklist = []
    return {
        "id": record.get("id"),
        "eTag": record.get("eTag"),
        "title": _todo_title(entity, content),
        "content": content,
        "listType": entity.get("listType"),
        "finished": entity.get("isFinish") == int(TodoItemState.YES),
        "remindType": entity.get("remindType", ReminderType.NO_SET),
        "remindRepeatType": entity.get("remindRepeatType", ReminderRepeatType.NOT_REPEAT),
        "remindTime": entity.get("remindTime", 0),
        "firstRemindTime": entity.get("firstRemindTime", 0),
        "createTime": entity.get("createTime", 0),
        "lastModifiedTime": entity.get("lastModifiedTime", 0),
        "checklist": checklist,
        "raw": record,
    }


def note_list(client: XiaomiClient, *, limit: int = 200) -> list[dict[str, Any]]:
    """Fetch and normalize note list output."""

    data = client.note_list(limit=limit)
    return data.get("entries", [])


def note_sync(client: XiaomiClient, *, sync_tag: str | None = None) -> dict[str, Any]:
    """Call the note sync endpoint."""

    return client.note_sync(sync_tag=sync_tag)


def todo_list(client: XiaomiClient, *, limit: int = 200) -> list[dict[str, Any]]:
    """Fetch and normalize todo list output."""

    data = client.todo_list(limit=limit)
    return [normalize_todo_record(item) for item in data.get("records", [])]


def todo_mark_finished(
    client: XiaomiClient,
    *,
    record_id: str | int,
    e_tag: str | int,
    record: dict[str, Any],
    finished: bool,
) -> Any:
    """Update a todo record's finished state."""

    normalized = normalize_todo_record(record)
    updated_record = build_todo_update_record(
        record,
        title=normalized["title"],
        checklist=normalized["checklist"],
        remind_at=normalized["remindTime"] or None,
        repeat=ReminderRepeatType(int(normalized["remindRepeatType"])),
        finished=finished,
    )
    return client.todo_update(record_id, e_tag, updated_record)


def _todo_title(entity: dict[str, Any], content: str) -> str:
    """Extract a user-facing todo title from raw content."""

    if entity.get("listType") == int(TodoListType.HAS_SON):
        try:
            parsed = json.loads(content)
            return parsed.get("title", "")
        except json.JSONDecodeError:
            return entity.get("plainText", "")
    return entity.get("plainText", content)
