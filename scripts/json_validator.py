#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 质量检测脚本 - 验证日报/资源/工程问题 JSON 格式

CLI:
    python scripts/json_validator.py --daily <path> [--fix]
    python scripts/json_validator.py --resource <path> [--fix]
    python scripts/json_validator.py --engineering <path> [--fix]

输出: {"passed": bool, "errors": [], "fixed": []}
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("Error: jsonschema is required. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


# 议题层级优先级映射
LEVEL_ORDER = {"⭐": 0, "🔄": 1, "💡": 2, "✅": 3}

# ==================== JSON Schemas ====================

DAILY_SCHEMA = {
    "type": "object",
    "required": ["type", "date", "topics"],
    "properties": {
        "type": {"const": "daily"},
        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "alerts": {"type": "array", "items": {"type": "string"}},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["time", "level", "content", "progress", "conclusion", "participants"],
                "properties": {
                    "time": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"},
                    "level": {"enum": ["⭐", "🔄", "💡", "✅"]},
                    "content": {"type": "string", "minLength": 1},
                    "progress": {"type": "string", "minLength": 1},
                    "conclusion": {"type": "string", "minLength": 1},
                    "participants": {"type": "array", "items": {"type": "string"}, "minItems": 1}
                }
            }
        },
        "trends": {
            "type": "object",
            "properties": {
                "phase_features": {"type": "array", "items": {"type": "string"}},
                "open_issues": {"type": "array", "items": {"type": "string"}}
            }
        },
        "active_members": {"type": "array", "items": {"type": "string"}}
    }
}

RESOURCE_SCHEMA = {
    "type": "object",
    "required": ["type", "date_range", "resources"],
    "properties": {
        "type": {"const": "resource"},
        "date_range": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["time", "title", "type", "summary", "content", "shared_by"],
                "properties": {
                    "time": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"},
                    "title": {"type": "string", "minLength": 1, "maxLength": 50},
                    "type": {"enum": ["链接", "paper", "其他", "知识文档", "开源项目", "网站", "文章", "新闻", "视频", "工具", "论坛", "技术博客", "活动"]},
                    "summary": {"type": "string", "minLength": 1},
                    "content": {"type": "string"},
                    "shared_by": {"type": "string"}
                }
            }
        }
    }
}

ENGINEERING_SCHEMA = {
    "type": "object",
    "required": ["type", "date_range", "issues"],
    "properties": {
        "type": {"const": "engineering"},
        "date_range": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["datetime", "group", "description", "solution", "tools", "status", "status_desc", "source"],
                "properties": {
                    "datetime": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$"},
                    "group": {"enum": ["部署与基础设施", "开发与调试工具", "记忆与进化机制", "生态与工具链", "成本控制与性能优化", "安全与合规", "Harness Engineering"]},
                    "description": {"type": "string", "minLength": 1},
                    "solution": {"type": "string", "minLength": 1},
                    "tools": {"type": "string"},
                    "status": {"enum": ["✅", "📝", "🔄", "⚠️"]},
                    "status_desc": {"type": "string", "minLength": 1, "maxLength": 20},
                    "source": {"type": "string"}
                }
            }
        }
    }
}

# Schema 映射
SCHEMAS = {
    "daily": DAILY_SCHEMA,
    "resource": RESOURCE_SCHEMA,
    "engineering": ENGINEERING_SCHEMA
}


class JSONValidator:
    """JSON 验证器"""

    def __init__(self, data: Dict[str, Any], data_type: str, filepath: Path):
        self.data = data
        self.data_type = data_type
        self.filepath = filepath
        self.errors: List[str] = []
        self.fixed: List[str] = []

    def validate(self) -> Dict[str, Any]:
        """执行完整验证流程"""
        # 1. Schema 验证
        self._validate_schema()

        # 2. 格式验证
        self._validate_format()

        # 3. 排序验证
        self._validate_sorting()

        return {
            "passed": len(self.errors) == 0,
            "errors": self.errors,
            "fixed": self.fixed
        }

    def _validate_schema(self):
        """使用 jsonschema 验证结构"""
        schema = SCHEMAS.get(self.data_type)
        if not schema:
            self.errors.append(f"Unknown data type: {self.data_type}")
            return

        try:
            validate(instance=self.data, schema=schema)
        except ValidationError as e:
            path = " -> ".join(str(p) for p in e.path) if e.path else "root"
            self.errors.append(f"Schema validation error at '{path}': {e.message}")

    def _validate_format(self):
        """验证字段格式"""
        if self.data_type == "daily":
            self._validate_daily_format()
        elif self.data_type == "resource":
            self._validate_resource_format()
        elif self.data_type == "engineering":
            self._validate_engineering_format()

    def _validate_daily_format(self):
        """验证日报格式"""
        # 检查日期格式
        date = self.data.get("date", "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            self.errors.append(f"Invalid date format: '{date}'. Expected 'YYYY-MM-DD'.")

        # 检查 topics 时间格式
        for i, topic in enumerate(self.data.get("topics", [])):
            time_val = topic.get("time", "")
            if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", time_val):
                self.errors.append(f"Topic {i}: Invalid time format: '{time_val}'. Expected 'YYYY-MM-DD HH:MM'.")

            # 检查 level 枚举
            level = topic.get("level", "")
            if level not in LEVEL_ORDER:
                self.errors.append(f"Topic {i}: Invalid level '{level}'. Expected one of: {list(LEVEL_ORDER.keys())}.")

    def _validate_resource_format(self):
        """验证资源格式"""
        # 检查 date_range
        date_range = self.data.get("date_range", [])
        if not (1 <= len(date_range) <= 2):
            self.errors.append(f"date_range must have 1-2 items, got {len(date_range)}.")
        else:
            for d in date_range:
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
                    self.errors.append(f"Invalid date in date_range: '{d}'. Expected 'YYYY-MM-DD'.")

        # 检查 resources 时间格式
        for i, res in enumerate(self.data.get("resources", [])):
            time_val = res.get("time", "")
            if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", time_val):
                self.errors.append(f"Resource {i}: Invalid time format: '{time_val}'. Expected 'YYYY-MM-DD HH:MM'.")

    def _validate_engineering_format(self):
        """验证工程问题格式"""
        # 检查 date_range
        date_range = self.data.get("date_range", [])
        if not (1 <= len(date_range) <= 2):
            self.errors.append(f"date_range must have 1-2 items, got {len(date_range)}.")
        else:
            for d in date_range:
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
                    self.errors.append(f"Invalid date in date_range: '{d}'. Expected 'YYYY-MM-DD'.")

        # 检查 issues 时间格式
        for i, issue in enumerate(self.data.get("issues", [])):
            time_val = issue.get("datetime", "")
            if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", time_val):
                self.errors.append(f"Issue {i}: Invalid datetime format: '{time_val}'. Expected 'YYYY-MM-DD HH:MM'.")

    def _validate_sorting(self):
        """验证排序"""
        if self.data_type == "daily":
            self._validate_topics_sorting()

    def _validate_topics_sorting(self):
        """验证 topics 按 level 排序"""
        topics = self.data.get("topics", [])
        current_order = [LEVEL_ORDER.get(t.get("level", ""), 99) for t in topics]

        # 检查是否按优先级排序
        for i in range(1, len(current_order)):
            if current_order[i] < current_order[i - 1]:
                self.errors.append(f"Topics not sorted by level. Expected order: ⭐ > 🔄 > 💡 > ✅")
                break

    def fix(self) -> Dict[str, Any]:
        """尝试自动修正问题"""
        original_errors = list(self.errors)
        self.errors = []  # 清空错误，重新验证

        # 1. 修正日期格式
        if self._fix_date_format():
            self.fixed.append("Fixed date format from filename")

        # 2. 修正 topics 排序
        if self.data_type == "daily" and self._fix_topics_sorting():
            self.fixed.append("Fixed topics sorting by level (⭐ > 🔄 > 💡 > ✅)")

        # 3. 重新验证
        result = self.validate()

        # 如果修正后仍有错误，恢复原始错误
        if not result["passed"] and result["errors"]:
            self.errors.extend([e for e in original_errors if e not in result["errors"]])

        return {
            "passed": len(self.errors) == 0,
            "errors": self.errors,
            "fixed": self.fixed
        }

    def _fix_date_format(self) -> bool:
        """从文件名提取日期并修正"""
        filename = self.filepath.stem
        # 尝试从文件名提取日期 (YYYY-MM-DD)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            extracted_date = date_match.group(1)
            if self.data.get("date") != extracted_date:
                self.data["date"] = extracted_date
                return True
        return False

    def _fix_topics_sorting(self) -> bool:
        """修正 topics 排序"""
        topics = self.data.get("topics", [])
        if len(topics) < 2:
            return False

        # 按优先级排序
        sorted_topics = sorted(topics, key=lambda t: LEVEL_ORDER.get(t.get("level", ""), 99))

        if sorted_topics != topics:
            self.data["topics"] = sorted_topics
            return True
        return False


def main():
    parser = argparse.ArgumentParser(description="Validate JSON schemas for qunribao reports")
    parser.add_argument("--daily", type=str, help="Path to daily report JSON")
    parser.add_argument("--resource", type=str, help="Path to resource JSON")
    parser.add_argument("--engineering", type=str, help="Path to engineering issues JSON")
    parser.add_argument("--fix", action="store_true", help="Auto-fix fixable issues")
    args = parser.parse_args()

    # 确定输入文件和类型
    input_path = None
    data_type = None

    if args.daily:
        input_path = Path(args.daily)
        data_type = "daily"
    elif args.resource:
        input_path = Path(args.resource)
        data_type = "resource"
    elif args.engineering:
        input_path = Path(args.engineering)
        data_type = "engineering"
    else:
        parser.error("Must specify one of: --daily, --resource, --engineering")

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

    # 验证
    validator = JSONValidator(data, data_type, input_path)
    if args.fix:
        result = validator.fix()
        # 如果有修正，写回文件
        if result["fixed"]:
            with open(input_path, 'w', encoding='utf-8') as f:
                json.dump(validator.data, f, ensure_ascii=False, indent=2)
            print(f"Fixed {len(result['fixed'])} issues and saved to {input_path}")
    else:
        result = validator.validate()

    # 输出结果
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)

    # 非零退出码表示验证失败
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
