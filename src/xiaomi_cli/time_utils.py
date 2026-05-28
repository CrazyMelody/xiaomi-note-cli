"""Time parsing helpers for Xiaomi Todo reminders."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

from .models import ReminderRepeatType


DEFAULT_TIMEZONE = "Asia/Shanghai"

REPEAT_ALIAS: dict[str, ReminderRepeatType] = {
    "none": ReminderRepeatType.NOT_REPEAT,
    "not_repeat": ReminderRepeatType.NOT_REPEAT,
    "daily": ReminderRepeatType.EVERY_DAY,
    "every_day": ReminderRepeatType.EVERY_DAY,
    "weekly": ReminderRepeatType.EVERY_WEEK,
    "every_week": ReminderRepeatType.EVERY_WEEK,
    "weekday": ReminderRepeatType.WEEKDAY,
    "monthly": ReminderRepeatType.EVERY_MONTH,
    "every_month": ReminderRepeatType.EVERY_MONTH,
    "yearly": ReminderRepeatType.EVERY_YEAR,
    "every_year": ReminderRepeatType.EVERY_YEAR,
}

RELATIVE_TIME_PATTERN = re.compile(
    r"^\s*(?P<count>\d+)\s*(?P<unit>秒|秒钟|分钟|分|小时|时|天|日|周)\s*后\s*$"
)
SHORT_RELATIVE_TIME_PATTERN = re.compile(
    r"^\s*(?P<count>\d+)\s*(?P<unit>[smhdw])\s*$",
    re.IGNORECASE,
)


def parse_remind_at(value: str, timezone: str = DEFAULT_TIMEZONE) -> int:
    """Parse a natural datetime string into epoch milliseconds.

    Args:
        value: Datetime string such as ``2026-05-29 09:30``.
        timezone: IANA timezone name.

    Returns:
        Unix timestamp in milliseconds.
    """

    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(timezone))
    return int(dt.timestamp() * 1000)


def parse_remind_in(
    value: str,
    *,
    timezone: str = DEFAULT_TIMEZONE,
    now: datetime | None = None,
) -> int:
    """Parse a relative reminder expression into epoch milliseconds.

    Args:
        value: Relative text such as ``5分钟后``、``1天后`` or ``1d``.
        timezone: IANA timezone name.
        now: Optional fixed reference time for tests.

    Returns:
        Unix timestamp in milliseconds.

    Raises:
        ValueError: If the expression is not supported.
    """

    matched = RELATIVE_TIME_PATTERN.match(value)
    short_matched = SHORT_RELATIVE_TIME_PATTERN.match(value)
    if not matched and not short_matched:
        raise ValueError(
            "不支持的 remind-in 值。示例：5分钟后、2小时后、1天后、1周后、1m、1h、1d、1w"
        )
    if matched:
        count = int(matched.group("count"))
        unit = matched.group("unit")
    else:
        count = int(short_matched.group("count"))
        unit = short_matched.group("unit").lower()
    current = now or datetime.now(ZoneInfo(timezone))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo(timezone))

    if unit in {"秒", "秒钟", "s"}:
        delta = timedelta(seconds=count)
    elif unit in {"分钟", "分", "m"}:
        delta = timedelta(minutes=count)
    elif unit in {"小时", "时", "h"}:
        delta = timedelta(hours=count)
    elif unit in {"天", "日", "d"}:
        delta = timedelta(days=count)
    else:
        delta = timedelta(weeks=count)
    return int((current + delta).timestamp() * 1000)


def format_timestamp(value: int | None, timezone: str = DEFAULT_TIMEZONE) -> str:
    """Format epoch milliseconds for display."""

    if not value:
        return "-"
    dt = datetime.fromtimestamp(value / 1000, tz=ZoneInfo(timezone))
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def parse_repeat(value: str | None) -> ReminderRepeatType:
    """Parse a user-facing repeat label into Xiaomi's repeat enum."""

    if value is None:
        return ReminderRepeatType.NOT_REPEAT
    normalized = value.strip().lower()
    if normalized not in REPEAT_ALIAS:
        supported = ", ".join(sorted(REPEAT_ALIAS))
        raise ValueError(f"不支持的 repeat 值：{value}。可选：{supported}")
    return REPEAT_ALIAS[normalized]
