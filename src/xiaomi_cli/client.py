"""HTTP client for Xiaomi web note and todo APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl
import json
import time

import httpx

from .config import AuthConfig
from .models import XiaomiResponse


BASE_URL = "https://i.mi.com"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


class XiaomiApiError(RuntimeError):
    """Raised when Xiaomi web APIs return a failure response."""


@dataclass(slots=True)
class XiaomiClient:
    """Thin HTTP client that mirrors the Xiaomi web app request format.

    Args:
        auth: Authentication config containing raw browser cookies.
        timeout: Request timeout in seconds.
    """

    auth: AuthConfig
    timeout: float = 20.0
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize an HTTP client with cookie jar and browser-like headers."""

        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=self.timeout,
            headers={
                "User-Agent": self.auth.user_agent or DEFAULT_USER_AGENT,
                "Referer": "https://i.mi.com/note/h5#/",
                "Origin": "https://i.mi.com",
                "Accept": "application/json, text/plain, */*",
            },
            cookies=self._parse_cookie_header(self.auth.cookie),
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    def save_cookie_file(self, output: Path) -> Path:
        """Write the raw cookie header into a plain-text file."""

        output.write_text(self.auth.cookie.strip() + "\n", encoding="utf-8")
        return output

    def get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        """Send a Xiaomi-style GET request.

        Args:
            path: Request path, with or without the leading slash.
            query: Query parameters.

        Returns:
            Decoded response data payload.
        """

        params = {"ts": int(time.time() * 1000)}
        if query:
            params.update({k: v for k, v in query.items() if v is not None})
        response = self._client.get(self._normalize_path(path), params=params)
        return self._unwrap_response(response)

    def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        """Send a Xiaomi-style POST request.

        Args:
            path: Request path, with or without the leading slash.
            body: Form payload.

        Returns:
            Decoded response data payload.
        """

        form = dict(body or {})
        if "serviceToken" not in form:
            token = self._client.cookies.get("serviceToken")
            if token:
                form["serviceToken"] = token
        encoded_form = self._flatten_form(form)
        response = self._client.post(
            self._normalize_path(path),
            data=encoded_form,
            headers={"content-type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        return self._unwrap_response(response)

    def note_has_data(self) -> Any:
        """Query whether the account has note data."""

        return self.get("/note/v2/hasData")

    def note_list(self, *, sync_tag: str | None = None, limit: int = 200) -> Any:
        """Fetch note entries and folders."""

        return self.get("/note/full/page", {"syncTag": sync_tag, "limit": limit})

    def note_detail(self, note_id: str) -> Any:
        """Fetch one note by id."""

        return self.get(f"/note/note/{note_id}/")

    def note_create(self, entry: dict[str, Any]) -> Any:
        """Create a note."""

        return self.post("/note/note", {"entry": json.dumps(entry, ensure_ascii=False)})

    def note_update(self, note_id: str, entry: dict[str, Any]) -> Any:
        """Update an existing note."""

        return self.post(
            f"/note/note/{note_id}",
            {"entry": json.dumps(entry, ensure_ascii=False)},
        )

    def note_delete(self, note_id: str, tag: str | int, *, purge: bool = False) -> Any:
        """Delete a note."""

        return self.post(f"/note/full/{note_id}/delete", {"tag": str(tag), "purge": purge})

    def note_sync(self, sync_tag: str | None = None) -> Any:
        """Sync note entries using the web sync endpoint."""

        payload = json.dumps({"note_view": {"syncTag": sync_tag}}, ensure_ascii=False)
        return self.get("/note/sync/full/", {"data": payload, "inactiveTime": 10})

    def note_index_check(self) -> Any:
        """Check note search index status."""

        return self.get("/note/index/check")

    def note_index_update(self) -> Any:
        """Trigger note search index update."""

        return self.post("/note/index/update")

    def todo_list(self, *, sync_token: dict[str, Any] | None = None, limit: int = 200) -> Any:
        """Fetch todo records."""

        return self.get(
            "/todo/v1/user/records",
            {"syncToken": json.dumps(sync_token, ensure_ascii=False) if sync_token else None, "limit": limit},
        )

    def todo_page(self, page_id: int | str) -> Any:
        """Fetch one todo page by page id used by the web app."""

        return self.get(f"/todo/v1/user/records/{page_id}")

    def todo_detail(self, record_id: int | str) -> Any:
        """Fetch one todo record by sync id."""

        return self.get(f"/todo/v1/user/records/{record_id}")

    def todo_create(self, record: dict[str, Any]) -> Any:
        """Create a todo record."""

        return self.post(
            "/todo/v1/user/records",
            {"record": json.dumps(record, ensure_ascii=False)},
        )

    def todo_update(self, record_id: int | str, previous_etag: str | int, record: dict[str, Any]) -> Any:
        """Update a todo record."""

        return self.post(
            f"/todo/v1/user/records/{record_id}/update",
            {
                "previousETag": str(previous_etag),
                "record": json.dumps(record, ensure_ascii=False),
            },
        )

    def todo_delete(self, record_id: int | str, previous_etag: str | int) -> Any:
        """Delete a todo record."""

        return self.post(
            f"/todo/v1/user/records/{record_id}/delete",
            {"prevETag": str(previous_etag)},
        )

    def _normalize_path(self, path: str) -> str:
        """Normalize a request path to Xiaomi's expected relative form."""

        return path if path.startswith("/") else f"/{path}"

    def _unwrap_response(self, response: httpx.Response) -> Any:
        """Validate a Xiaomi API response and return its data payload."""

        response.raise_for_status()
        payload = XiaomiResponse.model_validate(response.json())
        if payload.code not in (None, 0):
            raise XiaomiApiError(
                f"小米接口返回错误: code={payload.code}, result={payload.result}, description={payload.description}"
            )
        return payload.data

    @staticmethod
    def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
        """Convert a raw Cookie header string into a cookie dict."""

        cookie_map: dict[str, str] = {}
        for part in cookie_header.split(";"):
            chunk = part.strip()
            if not chunk or "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            cookie_map[key.strip()] = value.strip()
        if not cookie_map:
            # Accept already-urlencoded text as a last resort to aid debugging.
            cookie_map.update(dict(parse_qsl(cookie_header, keep_blank_values=True)))
        return cookie_map

    @classmethod
    def _flatten_form(cls, payload: dict[str, Any]) -> dict[str, str]:
        """Flatten nested request bodies into bracket-notation form fields.

        Args:
            payload: Nested request body.

        Returns:
            Flat mapping suitable for form submission.
        """

        flat: dict[str, str] = {}

        def walk(prefix: str, value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_prefix = f"{prefix}[{key}]" if prefix else str(key)
                    walk(child_prefix, child)
                return
            if isinstance(value, list):
                for index, child in enumerate(value):
                    child_prefix = f"{prefix}[{index}]"
                    walk(child_prefix, child)
                return
            if value is None:
                flat[prefix] = ""
            elif isinstance(value, bool):
                flat[prefix] = "true" if value else "false"
            else:
                flat[prefix] = str(value)

        for key, value in payload.items():
            walk(str(key), value)
        return flat
