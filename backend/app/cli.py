from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

from .analytics import AnalyticsService
from .config import Settings
from .database import Database
from .deployment import agent_config, normalize_platform, package_agent, validate_server_url, write_private_json
from .sync_service import SyncService


def main() -> None:
    parser = argparse.ArgumentParser(description="Token Dashboard maintenance CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("sync", help="同步 Codex 和 Hermes 数据")
    snapshot_parser = subparsers.add_parser("snapshot", help="同步并保存每日快照")
    snapshot_parser.add_argument("--day", help="YYYY-MM-DD；默认补齐所有缺失日期")
    subparsers.add_parser("health", help="输出本地数据库统计")
    backup_parser = subparsers.add_parser("backup", help="安全备份中心数据库")
    backup_parser.add_argument("--output", required=True)
    backup_parser.add_argument("--force", action="store_true")
    provision_parser = subparsers.add_parser(
        "provision-device", help="创建远程采集设备和密钥"
    )
    provision_parser.add_argument("--name", required=True)
    provision_parser.add_argument("--platform", choices=("windows", "macos"), required=True)
    provision_parser.add_argument("--codex-label")
    provision_parser.add_argument("--hermes-label")
    provision_parser.add_argument(
        "--server",
        required=True,
        help="远程设备可访问的看板地址，例如专属 Tailscale Serve HTTPS 地址",
    )
    provision_parser.add_argument("--output", help="将客户端配置写入 JSON 文件")
    package_parser = subparsers.add_parser(
        "package-agent", help="创建带独立设备密钥的采集端安装包"
    )
    package_parser.add_argument("--name", required=True)
    package_parser.add_argument("--platform", choices=("windows", "macos"), required=True)
    package_parser.add_argument("--server", required=True)
    package_parser.add_argument("--codex-label")
    package_parser.add_argument("--hermes-label")
    package_parser.add_argument("--template")
    package_parser.add_argument("--output", required=True)
    subparsers.add_parser("devices", help="列出采集设备")
    revoke_parser = subparsers.add_parser("revoke-device", help="吊销采集设备")
    revoke_parser.add_argument("device_id")
    args = parser.parse_args()

    settings = Settings.from_env()
    database = Database(settings.database_path)
    database.initialize()
    service = SyncService(database, settings)

    if args.command == "sync":
        result = service.sync_all()
    elif args.command == "snapshot":
        sync_result = service.sync_all()
        snapshot_result = (
            service.capture_snapshot(args.day)
            if args.day
            else service.capture_missing_snapshots()
        )
        result = {"sync": sync_result, "snapshot": snapshot_result}
    elif args.command == "health":
        with database.connect() as conn:
            result = {
                "database": str(database.path),
                "events": {
                    row["source"]: int(row["count"])
                    for row in conn.execute(
                        "SELECT source, COUNT(*) AS count FROM usage_events GROUP BY source"
                    ).fetchall()
                },
                "snapshots": conn.execute(
                    "SELECT COUNT(DISTINCT snapshot_day) FROM daily_snapshots"
                ).fetchone()[0],
            }
    elif args.command == "backup":
        output = Path(args.output).expanduser().resolve()
        if output == database.path.expanduser().resolve():
            raise ValueError("备份文件不能覆盖正在使用的数据库")
        if output.exists() and not args.force:
            raise FileExistsError(f"备份文件已经存在：{output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.unlink(missing_ok=True)
        try:
            with database.connect() as source, sqlite3.connect(temporary) as target:
                source.backup(target)
            os.replace(temporary, output)
            try:
                output.chmod(0o600)
            except OSError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
        result = {
            "status": "created",
            "backupPath": str(output),
            "bytes": output.stat().st_size,
            "warning": "备份包含完整 Token 历史和设备信息，请私密保存",
        }
    elif args.command in {"provision-device", "package-agent"}:
        platform_name = normalize_platform(args.platform)
        platform_label = "Windows" if platform_name == "windows" else "macOS"
        server_url = validate_server_url(args.server)
        result = database.provision_device(
            name=args.name,
            platform_name=platform_name,
            codex_label=args.codex_label or f"Codex · {args.name}",
            hermes_label=args.hermes_label or f"Hermes · {args.name}",
        )
        config = agent_config(
            server_url=server_url,
            device_id=result["deviceId"],
            device_name=result["deviceName"],
            device_token=result["token"],
            platform_name=platform_name,
            timezone_name=settings.timezone_name,
        )
        if args.command == "package-agent":
            project_root = Path(__file__).resolve().parents[2]
            template_name = (
                "Token-Dashboard-Agent-Windows-x64.template.zip"
                if platform_name == "windows"
                else "Token-Dashboard-Agent-macOS.template.zip"
            )
            template = Path(args.template).expanduser() if args.template else (
                project_root / "dist" / "templates" / template_name
            )
            output = Path(args.output).expanduser()
            package_agent(template, output, config)
            result = {
                "status": "created",
                "deviceId": result["deviceId"],
                "deviceName": result["deviceName"],
                "platform": platform_name,
                "packagePath": str(output),
                "warning": "安装包含独立设备密钥，安装完成后请删除传输副本",
            }
        elif args.output:
            output = Path(args.output).expanduser()
            write_private_json(output, config)
            result.pop("token", None)
            result["configPath"] = str(output)
            result["platform"] = platform_name
        else:
            result["platform"] = platform_name
            result["warning"] = "设备密钥只显示本次；请立即保存并避免复制到聊天或云盘"
    elif args.command == "devices":
        with database.connect() as conn:
            result = {
                "devices": [
                    dict(row)
                    for row in conn.execute(
                        """
                        SELECT id, name, platform, enabled, is_local,
                               last_seen_at, created_at, updated_at
                        FROM devices ORDER BY is_local DESC, name
                        """
                    ).fetchall()
                ]
            }
    else:
        with database.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE devices SET enabled = 0, updated_at = ?
                WHERE id = ? AND is_local = 0
                """,
                (time.time(), args.device_id),
            )
        result = {"status": "revoked", "deviceId": args.device_id, "updated": cursor.rowcount}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
