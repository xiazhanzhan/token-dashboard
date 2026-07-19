from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


APP_NAME = "Token Dashboard"
TIMEZONE_NAME = "Asia/Shanghai"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_path: Path
    codex_home: Path
    hermes_database_path: Path
    frontend_dist: Path
    sync_interval_seconds: int = 60
    timezone_name: str = TIMEZONE_NAME
    collect_local: bool = True

    @property
    def timezone(self):
        try:
            return ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            # The Windows embeddable Python runtime does not ship the IANA
            # timezone database. Keep the collector self-contained there.
            if self.timezone_name == TIMEZONE_NAME:
                return timezone(timedelta(hours=8), name=TIMEZONE_NAME)
            if self.timezone_name == "UTC":
                return timezone.utc
            raise

    @classmethod
    def from_env(cls) -> "Settings":
        home = Path.home()
        project_root = Path(__file__).resolve().parents[2]
        if os.name == "nt":
            default_data_dir = Path(
                os.environ.get("LOCALAPPDATA")
                or home / "AppData" / "Local"
            ) / APP_NAME
        elif platform.system() == "Darwin":
            default_data_dir = home / "Library" / "Application Support" / APP_NAME
        else:
            default_data_dir = Path(
                os.environ.get("XDG_DATA_HOME") or home / ".local" / "share"
            ) / "token-dashboard"
        data_dir = Path(
            os.environ.get(
                "TOKEN_DASHBOARD_DATA_DIR",
                default_data_dir,
            )
        ).expanduser()
        return cls(
            data_dir=data_dir,
            database_path=Path(
                os.environ.get(
                    "TOKEN_DASHBOARD_DB",
                    data_dir / "token-dashboard.sqlite3",
                )
            ).expanduser(),
            codex_home=Path(
                os.environ.get("TOKEN_DASHBOARD_CODEX_HOME", home / ".codex")
            ).expanduser(),
            hermes_database_path=Path(
                os.environ.get(
                    "TOKEN_DASHBOARD_HERMES_DB", home / ".hermes" / "state.db"
                )
            ).expanduser(),
            frontend_dist=Path(
                os.environ.get(
                    "TOKEN_DASHBOARD_FRONTEND_DIST",
                    project_root / "frontend" / "dist",
                )
            ).expanduser(),
            sync_interval_seconds=max(
                10, int(os.environ.get("TOKEN_DASHBOARD_SYNC_SECONDS", "60"))
            ),
            timezone_name=os.environ.get(
                "TOKEN_DASHBOARD_TIMEZONE", TIMEZONE_NAME
            ),
            collect_local=os.environ.get(
                "TOKEN_DASHBOARD_COLLECT_LOCAL", "1"
            ).strip().lower()
            not in {"0", "false", "no", "off"},
        )
