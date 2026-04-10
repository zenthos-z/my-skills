#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 转 Markdown 表格脚本

CLI:
    python scripts/json_to_md.py --input <json_path> --output <md_path>

支持类型:
- daily: 日报议题表格
- resource: 资源表格
- engineering: 工程问题表格
"""

import argparse
import json
import sys
from pathlib import Path


def json_to_markdown(data: dict, data_type: str) -> str:
    """
    将 JSON 数据转换为 Markdown 表格

    Args:
        data: JSON 数据
        data_type: 数据类型 (daily, resource, engineering)

    Returns:
        Markdown 表格字符串
    """
    if data_type == "resource":
        return _resource_to_markdown(data)
    elif data_type == "engineering":
        return _engineering_to_markdown(data)
    elif data_type == "daily":
        return _daily_to_markdown(data)
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def _resource_to_markdown(data: dict) -> str:
    """资源 JSON → Markdown 表格"""
    resources = data.get("resources", [])
    if not resources:
        return "# 资源分享\n\n暂无资源。"

    # 表头
    table = "| 时间段 | 资源标题 | 资源类型 | 资源简介 | 具体内容 | 分享人 |\n"
    table += "|--------|----------|----------|----------|----------|--------|\n"

    # 表格行
    for res in resources:
        time = res.get("time", "").replace(" ", "<br/>")
        title = res.get("title", "").replace("|", "\\|")
        res_type = res.get("type", "")
        summary = res.get("summary", "").replace("|", "\\|").replace("\n", "<br/>")
        content = res.get("content", "").replace("|", "\\|").replace("\n", "<br/>")
        shared_by = res.get("shared_by", "")

        table += f"| {time} | {title} | {res_type} | {summary} | {content} | {shared_by} |\n"

    return f"# 资源分享\n\n{table}"


def _engineering_to_markdown(data: dict) -> str:
    """工程问题 JSON → Markdown 表格"""
    issues = data.get("issues", [])
    if not issues:
        return "# 工程问题\n\n暂无工程问题。"

    # 表头
    table = "| 日期时间 | 问题分组 | 问题描述 | 解决方案 | 关键操作/工具 | 状态 | 状态描述 | 信息来源 |\n"
    table += "|----------|----------|----------|----------|----------------|------|----------|----------|\n"

    # 表格行
    for issue in issues:
        datetime_str = issue.get("datetime", "").replace(" ", "<br/>")
        group = issue.get("group", "")
        description = issue.get("description", "").replace("|", "\\|").replace("\n", "<br/>")
        solution = issue.get("solution", "").replace("|", "\\|").replace("\n", "<br/>")
        tools = issue.get("tools", "").replace("|", "\\|").replace("\n", "<br/>")
        status = issue.get("status", "")
        status_desc = issue.get("status_desc", "").replace("|", "\\|").replace("\n", "<br/>")
        source = issue.get("source", "").replace("|", "\\|").replace("\n", "<br/>")

        table += f"| {datetime_str} | {group} | {description} | {solution} | {tools} | {status} | {status_desc} | {source} |\n"

    return f"# 工程问题\n\n{table}"


def _daily_to_markdown(data: dict) -> str:
    """日报 JSON → Markdown 表格"""
    topics = data.get("topics", [])
    if not topics:
        return "## 议题概览\n\n暂无议题。"

    # 表头
    table = "| 时间段 | 议题层级 | 议题内容 | 进度 | 关键结论/产出/资源链接 | 参与人 |\n"
    table += "|--------|----------|----------|------|----------------------|--------|\n"

    # 表格行
    for topic in topics:
        time = topic.get("time", "").replace(" ", "<br/>")
        level = topic.get("level", "")
        content = topic.get("content", "").replace("|", "\\|").replace("\n", "<br/>")
        progress = topic.get("progress", "").replace("|", "\\|").replace("\n", "<br/>")
        conclusion = topic.get("conclusion", "").replace("|", "\\|").replace("\n", "<br/>")
        participants = ", ".join(topic.get("participants", []))

        table += f"| {time} | {level} | {content} | {progress} | {conclusion} | {participants} |\n"

    return table


def main():
    parser = argparse.ArgumentParser(description="Convert JSON to Markdown table")
    parser.add_argument("--input", type=str, required=True, help="Path to input JSON file")
    parser.add_argument("--output", type=str, required=True, help="Path to output Markdown file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 读取 JSON
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 检测类型
    data_type = data.get("type")
    if not data_type:
        print("Error: Missing 'type' field in JSON", file=sys.stderr)
        sys.exit(1)

    if data_type not in ["daily", "resource", "engineering"]:
        print(f"Error: Unknown type '{data_type}'. Expected: daily, resource, engineering", file=sys.stderr)
        sys.exit(1)

    # 转换
    try:
        markdown = json_to_markdown(data, data_type)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 写入文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"Converted {data_type} JSON to Markdown: {output_path}")


if __name__ == "__main__":
    main()
