#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书多维表格上传准备脚本 - 从 JSON 生成 lark-cli 命令

CLI:
    python scripts/feishu_upload.py --resource-json <path> --engineering-json <path> --config <config.local.md path>

输出: 包含 records 和 lark-cli 命令的 JSON
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加 scripts 目录到 path 以导入 config_loader
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir.parent))

try:
    from scripts.config_loader import ConfigLoader
except ImportError:
    print("Error: Cannot import config_loader. Make sure script is in correct location.", file=sys.stderr)
    sys.exit(1)


# UTC+8 时区
UTC_PLUS_8 = timezone(timedelta(hours=8))


def datetime_to_ms(date_str: str) -> int:
    """
    将 'YYYY-MM-DD HH:MM' 转换为 UTC+8 毫秒时间戳

    Args:
        date_str: 日期时间字符串

    Returns:
        毫秒时间戳
    """
    # 解析为 UTC+8 时间
    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    dt = dt.replace(tzinfo=UTC_PLUS_8)
    return int(dt.timestamp() * 1000)


def resource_to_bitable_record(resource: dict) -> dict:
    """
    将资源 JSON 转换为 Bitable record

    字段映射:
    - time -> 发布日期
    - title -> 资源标题
    - type -> 标签
    - summary -> 简介
    - content -> 具体内容
    - shared_by -> 分享人
    """
    return {
        "fields": {
            "发布日期": datetime_to_ms(resource.get("time", "")),
            "资源标题": resource.get("title", ""),
            "标签": [resource.get("type", "")],
            "简介": resource.get("summary", ""),
            "具体内容": resource.get("content", ""),
            "分享人": resource.get("shared_by", "")
        }
    }


def engineering_to_bitable_record(issue: dict) -> dict:
    """
    将工程问题 JSON 转换为 Bitable record

    字段映射:
    - datetime -> 日期
    - group -> 问题分组
    - description -> 问题描述
    - solution -> 解决方案
    - tools -> 关键操作/工具
    - status -> 状态
    - status_desc -> 状态描述
    - source -> 信息来源
    """
    return {
        "fields": {
            "日期": datetime_to_ms(issue.get("datetime", "")),
            "问题分组": issue.get("group", ""),
            "问题描述": issue.get("description", ""),
            "解决方案": issue.get("solution", ""),
            "关键操作/工具": issue.get("tools", ""),
            "状态": issue.get("status", ""),
            "状态描述": issue.get("status_desc", ""),
            "信息来源": issue.get("source", "")
        }
    }


def build_lark_cli_command(
    records: List[dict],
    app_token: str,
    table_id: str,
    lark_cli_path: str = "lark-cli"
) -> str:
    """
    构建 lark-cli 命令

    使用 lark-cli api 方式调用飞书多维表格接口：
    POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create

    注意：lark-cli api 子命令不支持 --id 参数，使用 --as bot 即可指定 bot 身份。

    Args:
        records: 要插入的记录列表
        app_token: Bitable app token
        table_id: 表 ID
        lark_cli_path: lark-cli 可执行文件名

    Returns:
        完整的 shell 命令字符串
    """
    api_path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

    # 构建 Bitable API 请求体
    body = {"records": records}
    body_json = json.dumps(body, ensure_ascii=False)

    cmd_parts = [
        "MSYS_NO_PATHCONV=1",
        lark_cli_path,
        "api",
        "POST",
        f'"{api_path}"',
        "--as bot",
        f"--data '{body_json}'"
    ]

    return " ".join(cmd_parts)


def main():
    parser = argparse.ArgumentParser(description="Prepare Feishu Bitable upload from JSON")
    parser.add_argument("--resource-json", type=str, help="Path to resource JSON file")
    parser.add_argument("--engineering-json", type=str, help="Path to engineering issues JSON file")
    parser.add_argument("--config", type=str, help="Path to config.local.md (default: assets/config.local.md)")
    args = parser.parse_args()

    # 至少需要一个输入
    if not args.resource_json and not args.engineering_json:
        parser.error("Must specify at least one of: --resource-json, --engineering-json")

    # 加载配置
    config_loader = ConfigLoader()
    if args.config:
        # 使用指定的配置文件路径
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        # 临时设置 assets 目录
        ConfigLoader.ASSETS_DIR = config_path.parent
    config = config_loader.load()

    # 获取飞书配置
    feishu_config = config.get("feishu", {})
    # 兼容驼峰和下划线两种命名
    bitable_app_token = feishu_config.get("bitableAppToken", feishu_config.get("resource_app_token", ""))
    resource_table_id = feishu_config.get("resourceTableId", feishu_config.get("resource_table_id", ""))
    engineering_table_id = feishu_config.get("engineeringTableId", feishu_config.get("engineering_table_id", ""))
    # 资源和工程表共用同一个 app token
    resource_app_token = bitable_app_token
    engineering_app_token = bitable_app_token

    # 验证配置
    if args.resource_json and (not resource_app_token or not resource_table_id):
        print("Error: Missing feishu resource_app_token or resource_table_id in config", file=sys.stderr)
        sys.exit(1)
    if args.engineering_json and (not engineering_app_token or not engineering_table_id):
        print("Error: Missing feishu engineering_app_token or engineering_table_id in config", file=sys.stderr)
        sys.exit(1)

    # 收集结果
    result = {
        "resources": [],
        "engineering": [],
        "commands": []
    }

    # 处理资源
    if args.resource_json:
        resource_path = Path(args.resource_json)
        if not resource_path.exists():
            print(f"Error: File not found: {resource_path}", file=sys.stderr)
            sys.exit(1)

        with open(resource_path, 'r', encoding='utf-8') as f:
            resource_data = json.load(f)

        for res in resource_data.get("resources", []):
            record = resource_to_bitable_record(res)
            result["resources"].append(record)

        if result["resources"]:
            cmd = build_lark_cli_command(
                result["resources"],
                resource_app_token,
                resource_table_id
            )
            result["commands"].append({
                "type": "resource",
                "command": cmd,
                "count": len(result["resources"])
            })

    # 处理工程问题
    if args.engineering_json:
        engineering_path = Path(args.engineering_json)
        if not engineering_path.exists():
            print(f"Error: File not found: {engineering_path}", file=sys.stderr)
            sys.exit(1)

        with open(engineering_path, 'r', encoding='utf-8') as f:
            engineering_data = json.load(f)

        for issue in engineering_data.get("issues", []):
            record = engineering_to_bitable_record(issue)
            result["engineering"].append(record)

        if result["engineering"]:
            cmd = build_lark_cli_command(
                result["engineering"],
                engineering_app_token,
                engineering_table_id
            )
            result["commands"].append({
                "type": "engineering",
                "command": cmd,
                "count": len(result["engineering"])
            })

    # 输出结果
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)


if __name__ == "__main__":
    main()
