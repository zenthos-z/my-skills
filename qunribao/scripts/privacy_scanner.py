#!/usr/bin/env python3
"""
Git pre-commit hook: 防止敏感信息泄露
安装在: .git/hooks/pre-commit
也可直接运行: python scripts/privacy_scanner.py
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class PrivacyScanner:
    """隐私信息扫描器"""

    # 检测规则 (正则表达式, 描述, 风险等级)
    RULES = [
        # 高危: API密钥
        (r'sk-[a-zA-Z0-9]{20,}', "API密钥 (sk-开头)", "CRITICAL"),

        # 中危: 微信群ID
        (r'\d{8,}@chatroom', "微信群ID", "HIGH"),

        # 中危: Windows绝对路径（含用户名）
        (r'[A-Z]:\\\w+\\\w+', "Windows绝对路径", "MEDIUM"),

        # 中危: 电话号码
        (r'1[3-9]\d{9}', "电话号码", "MEDIUM"),

        # 低危: 邮箱
        (r'[\w.-]+@[\w.-]+\.\w+', "邮箱地址", "LOW"),

        # 检查: 本地IP+端点
        (r'127\.0\.0\.1:\d{4,5}', "本地服务端点", "INFO"),
    ]

    # 白名单文件 (允许包含匹配内容)
    ALLOWLIST_FILES = {
        'config.json.example',
        'config.local.md',  # gitignored 本地配置，含真实值
        '.env.example',
        'config_loader.py',  # 配置加载器本身
        'pre-commit',  # 钩子本身
        'privacy_scanner.py',  # 扫描器本身
        'PRIVACY.md',  # 隐私说明文档
        '.gitignore',
    }

    # 白名单路径模式
    ALLOWLIST_PATHS = [
        r'\.claude/skills/dmx-image-gen/',  # dmx技能单独处理
    ]

    def __init__(self):
        self.issues: List[Tuple[str, int, str, str, str]] = []  # (file, line, match, type, level)

    def scan_file(self, filepath: Path) -> bool:
        """扫描单个文件，返回是否安全"""
        if filepath.name in self.ALLOWLIST_FILES:
            return True

        # 检查路径白名单
        path_str = str(filepath)
        for pattern in self.ALLOWLIST_PATHS:
            if re.search(pattern, path_str):
                return True

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return True  # 无法读取的文件跳过

        safe = True
        for pattern, desc, level in self.RULES:
            for line_num, line in enumerate(lines, 1):
                for match in re.finditer(pattern, line):
                    matched_text = match.group(0)

                    # 额外验证：排除误报
                    if self._is_false_positive(matched_text, desc, line):
                        continue

                    self.issues.append((str(filepath), line_num, matched_text, desc, level))
                    if level in ("CRITICAL", "HIGH"):
                        safe = False

        return safe

    def _is_false_positive(self, match: str, desc: str, line: str) -> bool:
        """判断是否为误报"""
        # 占位符不是隐私泄露
        if match.startswith('${') and match.endswith('}'):
            return True

        # 模板中的示例值
        if 'EXAMPLE' in line.upper() or 'PLACEHOLDER' in line.upper():
            return True

        return False

    def scan_staged_files(self) -> bool:
        """扫描git暂存区文件"""
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True,
            text=True
        )

        files = result.stdout.strip().split('\n') if result.stdout else []
        all_safe = True

        for filepath in files:
            if not filepath:
                continue
            path = Path(filepath)
            if not path.exists():
                continue

            # 只扫描文本文件
            if path.suffix in ['.py', '.json', '.md', '.txt', '.yml', '.yaml', '.sh']:
                if not self.scan_file(path):
                    all_safe = False

        return all_safe

    def scan_all_files(self, directory: Path = None) -> bool:
        """扫描目录下所有文件（用于CI模式）"""
        if directory is None:
            directory = Path.cwd()

        all_safe = True
        for ext in ['*.py', '*.json', '*.md', '*.txt', '*.yml', '*.yaml']:
            for filepath in directory.rglob(ext):
                # 跳过被gitignore的文件
                if '.git' in str(filepath):
                    continue
                if not self.scan_file(filepath):
                    all_safe = False

        return all_safe

    def report(self) -> str:
        """生成扫描报告"""
        if not self.issues:
            return "✓ 未发现隐私问题"

        lines = ["\n⚠️  发现潜在的隐私信息:", "=" * 60]

        # 按等级分组
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            level_issues = [i for i in self.issues if i[4] == level]
            if level_issues:
                lines.append(f"\n[{level}]")
                for filepath, line_num, match, desc, _ in level_issues:
                    lines.append(f"  {filepath}:{line_num}")
                    lines.append(f"    类型: {desc}")
                    lines.append(f"    内容: {match[:50]}{'...' if len(match) > 50 else ''}")

        lines.append("\n" + "=" * 60)
        lines.append("如果这是误报，请:\n")
        lines.append("1. 将占位符用于模板值: ${PLACEHOLDER}")
        lines.append("2. 或将文件加入扫描器白名单 (privacy_scanner.py:ALLOWLIST_FILES)")
        lines.append("3. 或使用 git commit --no-verify 强制提交（不推荐）")

        return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="隐私信息扫描器")
    parser.add_argument("--ci-mode", action="store_true", help="CI模式：扫描所有文件")
    parser.add_argument("--all", action="store_true", help="扫描所有文件")
    args = parser.parse_args()

    scanner = PrivacyScanner()

    if args.ci_mode or args.all:
        safe = scanner.scan_all_files()
        print("[CI模式] 扫描所有文件...")
    else:
        safe = scanner.scan_staged_files()

    print(scanner.report())

    if not safe:
        print("\n❌ 提交被阻止: 发现高危隐私信息")
        sys.exit(1)

    # 有中等风险时警告但允许
    medium_issues = [i for i in scanner.issues if i[4] == "MEDIUM"]
    if medium_issues:
        print(f"\n⚠️  警告: 发现 {len(medium_issues)} 个中风险项，但允许提交")

    print("\n✓ 提交通过检查")
    sys.exit(0)


if __name__ == '__main__':
    main()
