"""Tests for Xiaomi CLI service payload builders."""

from __future__ import annotations

from datetime import datetime
import json
from zoneinfo import ZoneInfo

from xiaomi_cli.models import ReminderRepeatType
from xiaomi_cli.services import (
    build_note_create_entry,
    build_note_update_entry,
    build_todo_record,
    build_todo_update_record,
)
from xiaomi_cli.time_utils import parse_remind_in


def test_build_todo_record_for_checklist() -> None:
    """Checklist todo creation should produce structured content."""

    record = build_todo_record(
        title="发布前检查",
        checklist=[{"content": "写文案", "isFinish": False}],
        remind_at=1770000000000,
        repeat=ReminderRepeatType.EVERY_DAY,
    )
    assert record["type"] == "entity"
    assert record["contentJson"]["listType"] == 1
    assert record["contentJson"]["remindRepeatType"] == 1
    content = json.loads(record["contentJson"]["content"])
    assert content["title"] == "发布前检查"


def test_build_todo_update_record_keeps_sync_fields() -> None:
    """Todo update should preserve sync-related fields from the source record."""

    source = {
        "id": "123",
        "eTag": "456",
        "type": "entity",
        "contentJson": {
            "syncId": "123",
            "syncEtag": "100",
            "createTime": 1700000000000,
            "lastModifiedTime": 1700000001000,
            "customSortId": 42,
            "content": "旧标题",
            "plainText": "旧标题",
            "listType": 0,
            "remindType": 0,
            "remindRepeatType": 0,
            "remindTime": 0,
            "firstRemindTime": 0,
            "expireTime": 0,
            "isFinish": 0,
            "markFinishTime": 0,
            "inputType": 0,
        },
    }
    record = build_todo_update_record(
        source,
        title="新标题",
        remind_at=1770000000000,
        repeat=ReminderRepeatType.EVERY_WEEK,
        finished=False,
    )
    assert record["id"] == "123"
    assert record["eTag"] == "456"
    assert record["contentJson"]["syncId"] == "123"
    assert record["contentJson"]["syncEtag"] == "100"
    assert record["contentJson"]["content"] == "新标题"
    assert record["contentJson"]["remindRepeatType"] == 2


def test_build_note_create_entry_has_minimal_fields() -> None:
    """Note create payload should match the minimal web-create shape."""

    entry = build_note_create_entry(content="hello", folder_id=0, color_id=0, alert_date=0)
    assert entry["content"] == "hello"
    assert "snippet" not in entry
    assert "subject" not in entry
    assert "extraInfo" not in entry


def test_build_note_update_entry_uses_extra_info_title() -> None:
    """Note update payload should mirror the web update structure."""

    source = {
        "id": "1",
        "tag": "2",
        "status": "normal",
        "createDate": 1700000000000,
        "modifyDate": 1700000001000,
        "colorId": 0,
        "folderId": 0,
        "alertDate": 0,
        "extraInfo": "{\"title\":\"旧标题\"}",
    }
    entry = build_note_update_entry(source, content="新正文", title="新标题")
    assert entry["id"] == "1"
    assert entry["tag"] == "2"
    assert entry["content"] == "新正文"
    assert "snippet" not in entry
    assert "subject" not in entry
    payload = json.loads(entry["extraInfo"])
    assert payload["title"] == "新标题"


def test_parse_remind_in_minutes() -> None:
    """Relative minute reminders should be converted from the current time."""

    base = datetime(2026, 5, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = parse_remind_in("5分钟后", now=base)
    assert result == 1779941100000


def test_parse_remind_in_days() -> None:
    """Relative day reminders should support Chinese natural expressions."""

    base = datetime(2026, 5, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = parse_remind_in("1天后", now=base)
    assert result == 1780027200000


def test_parse_remind_in_short_minutes() -> None:
    """Short remind-in format should support minute suffixes."""

    base = datetime(2026, 5, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = parse_remind_in("1m", now=base)
    assert result == 1779940860000


def test_parse_remind_in_short_hours() -> None:
    """Short remind-in format should support hour suffixes."""

    base = datetime(2026, 5, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = parse_remind_in("1h", now=base)
    assert result == 1779944400000
