from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .collectors.common import stable_id
from .config import Settings
from .database import Database
from .deployment import validate_server_url
from .sync_service import SyncService


def default_agent_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Token Dashboard Agent"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Token Dashboard Agent"
    return Path.home() / ".local" / "share" / "token-dashboard-agent"


def default_config_path() -> Path:
    configured = os.environ.get("TOKEN_DASHBOARD_AGENT_CONFIG")
    return Path(configured) if configured else default_agent_dir() / "agent-config.json"


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def load_config(path: Path) -> Dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"客户端配置不存在：{path}") from exc
    required = ("server_url", "device_id", "device_token")
    missing = [name for name in required if not config.get(name)]
    if missing:
        raise RuntimeError(f"客户端配置缺少字段：{', '.join(missing)}")
    if int(config.get("schema_version") or 1) != 1:
        raise RuntimeError("不支持的采集端配置版本")
    try:
        config["server_url"] = validate_server_url(str(config["server_url"]))
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return config


def agent_settings(config: Dict[str, Any]) -> Settings:
    configured_data_dir = config.get("data_dir")
    data_dir = (
        expand_path(str(configured_data_dir))
        if configured_data_dir
        else default_agent_dir()
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    codex_home = expand_path(str(config.get("codex_home") or "~/.codex"))
    hermes_database = expand_path(
        str(config.get("hermes_database_path") or "~/.hermes/state.db")
    )
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "agent.sqlite3",
        codex_home=codex_home,
        hermes_database_path=hermes_database,
        frontend_dist=data_dir / "no-frontend",
        sync_interval_seconds=max(30, int(config.get("sync_interval_seconds") or 60)),
        timezone_name=str(config.get("timezone") or "Asia/Shanghai"),
    )


def configure_logging(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(data_dir / "agent.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def chunks(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


class TokenAgent:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.settings = agent_settings(self.config)
        configure_logging(self.settings.data_dir)
        self.database = Database(self.settings.database_path)
        self.database.initialize()
        self.sync_service = SyncService(self.database, self.settings)
        self.destination_id = stable_id(
            "destination", self.config["server_url"].rstrip("/")
        )

    def _pending_rows(self, limit: int = 1000) -> List[Dict[str, Any]]:
        with self.database.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT e.*
                    FROM usage_events e
                    LEFT JOIN agent_delivery d
                      ON d.destination_id = ? AND d.event_id = e.id
                    WHERE d.event_id IS NULL
                    ORDER BY e.occurred_at, e.id
                    LIMIT ?
                    """
                    ,
                    (self.destination_id, limit),
                ).fetchall()
            ]

    def _remote_event(self, row: Dict[str, Any]) -> Dict[str, Any]:
        source = str(row["source"])
        account_keys = self.config.get("account_keys") or {}
        account_labels = self.config.get("account_labels") or {}
        account_key = str(account_keys.get(source) or source)
        session_hash = hashlib.sha256(
            f"{account_key}\0{source}\0{row['external_session_id']}".encode("utf-8")
        ).hexdigest()
        try:
            metadata = json.loads(str(row.get("metadata_json") or "{}"))
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return {
            "schemaVersion": 1,
            "eventId": stable_id("remote-event", account_key, row["id"]),
            "source": source,
            "accountKey": account_key,
            "accountLabel": str(account_labels.get(source) or "").strip() or None,
            "sessionHash": session_hash,
            "occurredAt": float(row["occurred_at"]),
            "model": row["model"] or "unknown",
            "inputTokens": int(row["input_tokens"]),
            "cacheReadTokens": int(row["cache_read_tokens"]),
            "cacheWriteTokens": int(row["cache_write_tokens"]),
            "outputTokens": int(row["output_tokens"]),
            "reasoningTokens": int(row["reasoning_tokens"]),
            "totalTokens": int(row["total_tokens"]),
            "replaceSession": bool(metadata.get("replace_session")),
        }

    def _ssl_context(self) -> ssl.SSLContext:
        try:
            import certifi  # type: ignore

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def _post(self, body: Dict[str, Any]) -> Dict[str, Any]:
        url = self.config["server_url"].rstrip("/") + "/api/v1/ingest/events"
        request = urllib.request.Request(
            url,
            data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['device_token']}",
                "User-Agent": f"TokenDashboardAgent/1 ({platform.system()})",
            },
        )
        # The endpoint is a Tailscale-only address. Bypass OS HTTP proxies so a
        # desktop proxy cannot intercept or reject the private 100.64/10 route.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=self._ssl_context()),
        )
        try:
            with opener.open(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"服务器拒绝上报：HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接中心主机：{exc.reason}") from exc

    def upload(self) -> Dict[str, int]:
        pending_total = 0
        uploaded = 0
        batches = 0
        while True:
            pending = self._pending_rows()
            if not pending:
                break
            pending_total += len(pending)
            for group in chunks(pending, 200):
                ids = [str(row["id"]) for row in group]
                events = [self._remote_event(row) for row in group]
                batch_id = stable_id(
                    "agent-batch",
                    self.config["device_id"],
                    self.config.get("profile_id") or "default",
                    events,
                )
                payload = {
                    "schemaVersion": 1,
                    "batchId": batch_id,
                    "events": events,
                }
                result = self._post(payload)
                if result.get("status") not in {"ok", "duplicate_batch"}:
                    raise RuntimeError(f"服务器返回未知状态：{result}")
                now = time.time()
                with self.database.transaction() as conn:
                    conn.executemany(
                        """
                        INSERT OR REPLACE INTO agent_delivery (
                            destination_id, event_id, uploaded_at, batch_id
                        ) VALUES (?, ?, ?, ?)
                        """,
                        [
                            (self.destination_id, event_id, now, batch_id)
                            for event_id in ids
                        ],
                    )
                uploaded += len(group)
                batches += 1
        return {"pending": pending_total, "uploaded": uploaded, "batches": batches}

    def sync_once(self) -> Dict[str, Any]:
        sync_result = self.sync_service.sync_all()
        upload_result = self.upload()
        result = {"sync": sync_result, "upload": upload_result}
        logging.info("同步完成：%s", json.dumps(result, ensure_ascii=False))
        return result

    def status(self) -> Dict[str, Any]:
        with self.database.connect() as conn:
            events = conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
            pending = conn.execute(
                """
                SELECT COUNT(*) FROM usage_events e
                LEFT JOIN agent_delivery d
                  ON d.destination_id = ? AND d.event_id = e.id
                WHERE d.event_id IS NULL
                """
                ,
                (self.destination_id,),
            ).fetchone()[0]
        return {
            "deviceId": self.config["device_id"],
            "deviceName": self.config.get("device_name"),
            "server": self.config["server_url"],
            "codexHome": str(self.settings.codex_home),
            "hermesDatabase": str(self.settings.hermes_database_path),
            "events": int(events),
            "pending": int(pending),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Token Dashboard remote collector")
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("command", choices=("sync", "run", "status"), nargs="?", default="sync")
    args = parser.parse_args()
    agent = TokenAgent(args.config)
    if args.command == "status":
        result = agent.status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "sync":
        result = agent.sync_once()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    interval = agent.settings.sync_interval_seconds
    logging.info("采集客户端已启动，每 %s 秒同步", interval)
    while True:
        try:
            agent.sync_once()
        except Exception:
            logging.exception("同步失败；稍后自动重试")
        time.sleep(interval)


if __name__ == "__main__":
    main()
