"""Typer-based CLI for Xiaomi Notes and Todo."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any
import json
import time

from rich import print
from rich.console import Console
from rich.table import Table
import typer

from .client import XiaomiClient
from .config import DEFAULT_CONFIG_FILE, load_auth_config, save_auth_config
from .services import (
    build_note_create_entry,
    build_note_update_entry,
    build_todo_record,
    build_todo_update_record,
    note_list,
    note_sync,
    normalize_todo_record,
    todo_list,
    todo_mark_finished,
)
from .time_utils import format_timestamp, parse_remind_at, parse_remind_in, parse_repeat


console = Console()
app = typer.Typer(help="小米云笔记 / 待办 CLI")
auth_app = typer.Typer(help="认证与配置")
note_app = typer.Typer(help="笔记操作")
todo_app = typer.Typer(help="待办操作")
sync_app = typer.Typer(help="同步相关操作")

app.add_typer(auth_app, name="auth")
app.add_typer(note_app, name="note")
app.add_typer(todo_app, name="todo")
app.add_typer(sync_app, name="sync")


CookieOption = Annotated[str | None, typer.Option(help="直接传入完整 Cookie header")]
CookieFileOption = Annotated[Path | None, typer.Option(help="包含完整 Cookie header 的文件路径")]
UserAgentOption = Annotated[str | None, typer.Option(help="自定义 User-Agent")]


def main() -> None:
    """CLI entry point."""

    app()


def _client_from_options(
    *,
    cookie: str | None,
    cookie_file: Path | None,
    user_agent: str | None,
) -> XiaomiClient:
    """Build an authenticated Xiaomi API client."""

    auth = load_auth_config(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    return XiaomiClient(auth=auth)


@auth_app.command("save")
def auth_save(
    cookie: Annotated[str, typer.Option(prompt=True, hide_input=True, help="浏览器里复制出来的完整 Cookie header")],
    user_agent: UserAgentOption = None,
) -> None:
    """Save cookie config locally for later commands."""

    output = save_auth_config(cookie, user_agent=user_agent)
    print(f"[green]已保存认证配置[/green]：{output}")


@auth_app.command("show-path")
def auth_show_path() -> None:
    """Show the default config path."""

    print(str(DEFAULT_CONFIG_FILE))


@note_app.command("list")
def note_list_cmd(
    limit: Annotated[int, typer.Option(help="最多返回多少条")] = 50,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """List notes."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        entries = note_list(client, limit=limit)
    finally:
        client.close()

    table = Table(title="笔记列表")
    table.add_column("ID")
    table.add_column("标题")
    table.add_column("文件夹")
    table.add_column("修改时间")
    for item in entries:
        table.add_row(
            str(item.get("id", "")),
            str(item.get("subject") or "").strip(),
            str(item.get("folderId", "")),
            format_timestamp(item.get("modifyDate")),
        )
    console.print(table)


@note_app.command("get")
def note_get_cmd(
    note_id: Annotated[str, typer.Argument(help="笔记 ID")],
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Get one note detail."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.note_detail(note_id)
    finally:
        client.close()
    print_json(data)


@note_app.command("create")
def note_create_cmd(
    content: Annotated[str, typer.Option(help="笔记正文内容")],
    folder_id: Annotated[str, typer.Option(help="文件夹 ID")] = "0",
    color_id: Annotated[int, typer.Option(help="颜色 ID")] = 0,
    alert_date: Annotated[int, typer.Option(help="提醒时间戳，毫秒")] = 0,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Create a note."""

    entry = build_note_create_entry(
        content=content,
        folder_id=folder_id,
        color_id=color_id,
        alert_date=alert_date,
    )
    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.note_create(entry)
    finally:
        client.close()
    print_json(data)


@note_app.command("update")
def note_update_cmd(
    note_id: Annotated[str, typer.Argument(help="笔记 ID")],
    content: Annotated[str, typer.Option(help="新的正文内容")],
    tag: Annotated[str | None, typer.Option(help="当前笔记 tag，建议先用 note get 查看")] = None,
    title: Annotated[str, typer.Option(help="标题")] = "",
    folder_id: Annotated[str | None, typer.Option(help="文件夹 ID")] = None,
    color_id: Annotated[int | None, typer.Option(help="颜色 ID")] = None,
    alert_date: Annotated[int | None, typer.Option(help="提醒时间戳，毫秒")] = None,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Update a note."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        detail = client.note_detail(note_id)["entry"]
        entry = build_note_update_entry(
            detail,
            content=content,
            title=title,
            folder_id=folder_id,
            color_id=color_id,
            alert_date=alert_date,
        )
        if tag:
            entry["tag"] = str(tag)
        data = client.note_update(note_id, entry)
    finally:
        client.close()
    print_json(data)


@note_app.command("delete")
def note_delete_cmd(
    note_id: Annotated[str, typer.Argument(help="笔记 ID")],
    tag: Annotated[str, typer.Option(help="当前笔记 tag，必填")] = ...,
    purge: Annotated[bool, typer.Option(help="是否彻底删除")] = False,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Delete a note."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.note_delete(note_id, tag, purge=purge)
    finally:
        client.close()
    print_json(data)


@todo_app.command("list")
def todo_list_cmd(
    limit: Annotated[int, typer.Option(help="最多返回多少条")] = 50,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """List todo records."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        records = todo_list(client, limit=limit)
    finally:
        client.close()

    table = Table(title="待办列表")
    table.add_column("ID")
    table.add_column("标题")
    table.add_column("状态")
    table.add_column("提醒时间")
    table.add_column("重复")
    for item in records:
        table.add_row(
            str(item["id"]),
            str(item["title"]),
            "已完成" if item["finished"] else "未完成",
            format_timestamp(item["remindTime"]),
            str(item["remindRepeatType"]),
        )
    console.print(table)


@todo_app.command("get")
def todo_get_cmd(
    record_id: Annotated[str, typer.Argument(help="待办记录 ID")],
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Get one todo record."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.todo_detail(record_id)
    finally:
        client.close()
    print_json(data)


@todo_app.command("create")
def todo_create_cmd(
    title: Annotated[str, typer.Option(help="待办标题")],
    checklist: Annotated[list[str] | None, typer.Option(help="子任务，可多次传入 --checklist")] = None,
    remind_at: Annotated[str | None, typer.Option(help="提醒时间，例如 2026-05-29 09:30")] = None,
    remind_in: Annotated[str | None, typer.Option(help="相对提醒时间，例如 5分钟后、1天后、1m、1h、1d")] = None,
    repeat: Annotated[str | None, typer.Option(help="重复规则：none/daily/weekly/weekday/monthly/yearly")] = None,
    finished: Annotated[bool, typer.Option(help="是否创建为已完成")] = False,
    custom_sort_id: Annotated[int, typer.Option(help="自定义排序值")] = 0,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Create a todo record."""

    remind_ts = _resolve_remind_time(remind_at=remind_at, remind_in=remind_in)
    repeat_value = parse_repeat(repeat)
    record = build_todo_record(
        title=title,
        checklist=[{"content": item, "isFinish": False} for item in (checklist or [])],
        remind_at=remind_ts,
        repeat=repeat_value,
        finished=finished,
        custom_sort_id=custom_sort_id,
    )
    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.todo_create(record)
    finally:
        client.close()
    print_json(data)


@todo_app.command("update")
def todo_update_cmd(
    record_id: Annotated[str, typer.Argument(help="待办记录 ID")],
    title: Annotated[str, typer.Option(help="新的标题")],
    e_tag: Annotated[str, typer.Option(help="当前记录 eTag，建议先用 todo get 查看")] = ...,
    checklist: Annotated[list[str] | None, typer.Option(help="新的子任务列表，可多次传入 --checklist")] = None,
    remind_at: Annotated[str | None, typer.Option(help="提醒时间，例如 2026-05-29 09:30；传空字符串不改")] = None,
    remind_in: Annotated[str | None, typer.Option(help="相对提醒时间，例如 5分钟后、1天后、1m、1h、1d")] = None,
    repeat: Annotated[str | None, typer.Option(help="重复规则：none/daily/weekly/weekday/monthly/yearly")] = None,
    finished: Annotated[bool | None, typer.Option(help="是否标记为完成")] = None,
    custom_sort_id: Annotated[int, typer.Option(help="自定义排序值")] = 0,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Update a todo record."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        raw = client.todo_detail(record_id)
        source_record = raw.get("record", raw)
        normalized = normalize_todo_record(source_record)
        resolved_remind_ts = _resolve_remind_time(remind_at=remind_at, remind_in=remind_in)
        remind_ts = resolved_remind_ts if resolved_remind_ts is not None else normalized["remindTime"] or None
        if repeat is not None:
            repeat_value = parse_repeat(repeat)
        elif remind_ts:
            repeat_value = parse_repeat(_repeat_name(int(normalized["remindRepeatType"])))
        else:
            repeat_value = parse_repeat("none")
        record = build_todo_update_record(
            source_record,
            title=title,
            checklist=[{"content": item, "isFinish": False} for item in checklist] if checklist is not None else None,
            remind_at=remind_ts,
            repeat=repeat_value,
            finished=normalized["finished"] if finished is None else finished,
            custom_sort_id=None if custom_sort_id == 0 else custom_sort_id,
        )
        data = client.todo_update(record_id, e_tag, record)
    finally:
        client.close()
    print_json(data)


@todo_app.command("delete")
def todo_delete_cmd(
    record_id: Annotated[str, typer.Argument(help="待办记录 ID")],
    e_tag: Annotated[str, typer.Option(help="当前记录 eTag，必填")] = ...,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Delete a todo record."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.todo_delete(record_id, e_tag)
    finally:
        client.close()
    print_json(data)


@todo_app.command("finish")
def todo_finish_cmd(
    record_id: Annotated[str, typer.Argument(help="待办记录 ID")],
    e_tag: Annotated[str, typer.Option(help="当前记录 eTag，必填")] = ...,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Mark a todo record as finished."""

    _todo_finish_toggle(record_id, e_tag, True, cookie, cookie_file, user_agent)


@todo_app.command("unfinish")
def todo_unfinish_cmd(
    record_id: Annotated[str, typer.Argument(help="待办记录 ID")],
    e_tag: Annotated[str, typer.Option(help="当前记录 eTag，必填")] = ...,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Mark a todo record as unfinished."""

    _todo_finish_toggle(record_id, e_tag, False, cookie, cookie_file, user_agent)


@sync_app.command("notes")
def sync_notes_cmd(
    sync_tag: Annotated[str | None, typer.Option(help="已有 syncTag，可选")] = None,
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Call note sync endpoint."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = note_sync(client, sync_tag=sync_tag)
    finally:
        client.close()
    print_json(data)


@sync_app.command("index-check")
def sync_index_check_cmd(
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Check note index status."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.note_index_check()
    finally:
        client.close()
    print_json(data)


@sync_app.command("index-update")
def sync_index_update_cmd(
    cookie: CookieOption = None,
    cookie_file: CookieFileOption = None,
    user_agent: UserAgentOption = None,
) -> None:
    """Trigger note index update."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        data = client.note_index_update()
    finally:
        client.close()
    print_json(data)


def _todo_finish_toggle(
    record_id: str,
    e_tag: str,
    finished: bool,
    cookie: str | None,
    cookie_file: Path | None,
    user_agent: str | None,
) -> None:
    """Shared helper for finish/unfinish commands."""

    client = _client_from_options(cookie=cookie, cookie_file=cookie_file, user_agent=user_agent)
    try:
        raw = client.todo_detail(record_id)
        source_record = raw.get("record", raw)
        data = todo_mark_finished(
            client,
            record_id=record_id,
            e_tag=e_tag,
            record=source_record,
            finished=finished,
        )
    finally:
        client.close()
    print_json(data)


def _repeat_name(value: int) -> str:
    """Convert repeat enum values back into CLI-friendly names."""

    mapping = {
        0: "none",
        1: "daily",
        2: "weekly",
        3: "weekday",
        7: "monthly",
        8: "yearly",
    }
    return mapping.get(value, "none")


def print_json(data: Any) -> None:
    """Pretty-print JSON data in UTF-8."""

    console.print_json(json=json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _resolve_remind_time(*, remind_at: str | None, remind_in: str | None) -> int | None:
    """Resolve absolute or relative reminder input into epoch milliseconds.

    Args:
        remind_at: Absolute reminder time.
        remind_in: Relative reminder time.

    Returns:
        Parsed timestamp in milliseconds, or ``None`` when neither is provided.

    Raises:
        typer.BadParameter: If both inputs are provided.
    """

    if remind_at and remind_in:
        raise typer.BadParameter("`--remind-at` 和 `--remind-in` 不能同时传。")
    if remind_at:
        return parse_remind_at(remind_at)
    if remind_in:
        return parse_remind_in(remind_in)
    return None
