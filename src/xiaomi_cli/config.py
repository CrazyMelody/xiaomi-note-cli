"""Configuration helpers for the Xiaomi CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "xiaomi-cli"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass(slots=True)
class AuthConfig:
    """Authentication settings used for Xiaomi web API requests.

    Args:
        cookie: Raw Cookie header string copied from the logged-in browser.
        user_agent: Optional user agent override for requests.
    """

    cookie: str
    user_agent: str | None = None


def ensure_config_dir() -> Path:
    """Create and return the config directory.

    Side effects:
        Creates the directory if it does not already exist.
    """

    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def load_auth_config(
    *,
    cookie: str | None = None,
    cookie_file: Path | None = None,
    user_agent: str | None = None,
) -> AuthConfig:
    """Load authentication config from CLI arguments, env vars, or config file.

    Args:
        cookie: Raw cookie string passed from the command line.
        cookie_file: Path to a file containing only the cookie header value.
        user_agent: Optional user agent override.

    Returns:
        Parsed authentication configuration.

    Raises:
        ValueError: If no usable cookie can be found.
    """

    resolved_cookie = (
        cookie
        or _read_cookie_file(cookie_file)
        or os.environ.get("XIAOMI_COOKIE")
        or _load_cookie_from_config_file()
    )
    resolved_user_agent = (
        user_agent
        or os.environ.get("XIAOMI_USER_AGENT")
        or _load_user_agent_from_config_file()
    )
    if not resolved_cookie:
        raise ValueError(
            "未找到可用的 Cookie。请使用 --cookie / --cookie-file，或先执行 `xiaomi-cli auth save`。"
        )
    return AuthConfig(cookie=resolved_cookie.strip(), user_agent=resolved_user_agent)


def save_auth_config(cookie: str, user_agent: str | None = None) -> Path:
    """Persist authentication config to the default config file.

    Args:
        cookie: Raw cookie string copied from the browser.
        user_agent: Optional user agent string.

    Returns:
        The config file path that was written.
    """

    ensure_config_dir()
    data = {"cookie": cookie.strip()}
    if user_agent:
        data["user_agent"] = user_agent.strip()
    DEFAULT_CONFIG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return DEFAULT_CONFIG_FILE


def _read_cookie_file(cookie_file: Path | None) -> str | None:
    """Read cookie string from a plain-text file."""

    if cookie_file is None:
        return None
    return cookie_file.read_text(encoding="utf-8").strip()


def _load_cookie_from_config_file() -> str | None:
    """Load cookie value from the default JSON config file."""

    data = _load_json_config()
    value = data.get("cookie")
    return value if isinstance(value, str) and value.strip() else None


def _load_user_agent_from_config_file() -> str | None:
    """Load user agent value from the default JSON config file."""

    data = _load_json_config()
    value = data.get("user_agent")
    return value if isinstance(value, str) and value.strip() else None


def _load_json_config() -> dict[str, object]:
    """Read the default JSON config if it exists."""

    if not DEFAULT_CONFIG_FILE.exists():
        return {}
    try:
        content = DEFAULT_CONFIG_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
