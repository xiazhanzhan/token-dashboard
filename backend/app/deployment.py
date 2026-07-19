from __future__ import annotations

import json
import os
import platform
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse


PLATFORM_ALIASES = {
    "darwin": "macos",
    "mac": "macos",
    "macos": "macos",
    "win": "windows",
    "win32": "windows",
    "windows": "windows",
}


def normalize_platform(value: str) -> str:
    normalized = PLATFORM_ALIASES.get(value.strip().lower())
    if normalized is None:
        raise ValueError("平台必须是 windows 或 macos")
    return normalized


def current_platform() -> str:
    return "windows" if os.name == "nt" else normalize_platform(platform.system())


def validate_server_url(server_url: str) -> str:
    value = server_url.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc:
        return value
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return value
    raise ValueError("远程主机地址必须使用 HTTPS；只有本机 localhost 可以使用 HTTP")


def agent_config(
    *,
    server_url: str,
    device_id: str,
    device_name: str,
    device_token: str,
    platform_name: str,
    timezone_name: str = "Asia/Shanghai",
    sync_interval_seconds: int = 60,
) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "server_url": validate_server_url(server_url),
        "device_id": device_id,
        "device_name": device_name,
        "device_token": device_token,
        "platform": normalize_platform(platform_name),
        "timezone": timezone_name,
        "sync_interval_seconds": max(30, int(sync_interval_seconds)),
    }


def write_private_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def package_agent(template: Path, output: Path, config: Dict[str, Any]) -> Path:
    """Inject a one-device credential into a credential-free agent template."""
    if not template.is_file():
        raise FileNotFoundError(f"采集端模板不存在：{template}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="token-dashboard-agent-") as temporary:
        stage = Path(temporary) / "package"
        stage.mkdir()
        with zipfile.ZipFile(template) as archive:
            archive.extractall(stage)
        if (stage / "agent-config.json").exists():
            raise ValueError("采集端模板中不应包含设备密钥")
        write_private_json(stage / "agent-config.json", config)
        temporary_zip = Path(temporary) / "agent.zip"
        with zipfile.ZipFile(
            temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for item in sorted(stage.rglob("*")):
                if item.is_file():
                    archive.write(item, item.relative_to(stage))
        shutil.copyfile(temporary_zip, output)
    try:
        output.chmod(0o600)
    except OSError:
        pass
    return output
