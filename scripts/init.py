#!/usr/bin/env python3
"""
qunribao 初始化向导
引导新开发者创建本地配置
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any


class InitWizard:
    def __init__(self):
        # 定位到技能目录
        self.skill_dir = Path(__file__).parent.parent
        self.assets_dir = self.skill_dir / "assets"
        self.config_template_path = self.assets_dir / "config.json"
        self.config_local_path = self.assets_dir / "config.local.md"

    def run(self):
        """运行初始化向导"""
        print("=" * 60)
        print("  qunribao 初始化向导")
        print("=" * 60)
        print()

        # 检查是否已存在本地配置
        if self.config_local_path.exists():
            print(f"⚠️  本地配置已存在: {self.config_local_path}")
            response = input("是否覆盖? [y/N]: ").strip().lower()
            if response != 'y':
                print("已取消")
                return

        # 加载模板
        template = self._load_template()

        # 交互式收集配置
        config = self._collect_config(template)

        # 保存配置
        self._save_config(config)

        # 设置git hooks
        self._setup_git_hooks()

        print()
        print("=" * 60)
        print("  ✓ 初始化完成!")
        print("=" * 60)
        print()
        print("下一步:")
        print("1. 编辑 config.local.md 以更新配置")
        print("2. 运行: python scripts/render_templates.py")
        print("3. 开始使用 qunribao!")

    def _load_template(self) -> Dict[str, Any]:
        """返回默认配置值"""
        return {
            'valueTopics': [
                '强制隔离下的任务编排',
                '约束工程 & Harness Engineering',
                '记忆机制',
                '世界模型',
                '强化学习',
                '可视化调试',
            ],
            'engineeringGroups': [
                '部署与基础设施',
                '开发与调试工具',
                '记忆与进化机制',
                '生态与工具链',
                '成本控制与性能优化',
                '安全与合规',
            ],
        }

    def _collect_config(self, template: Dict) -> Dict[str, Any]:
        """交互式收集配置值"""
        config = {}

        print("请提供以下配置信息（直接回车使用示例值）:\n")

        # 群聊配置
        print("[群聊配置]")
        chatroom_id = input("群ID (如: 123456789@chatroom): ").strip()
        config['chatroomId'] = chatroom_id or "YOUR_CHATROOM_ID@chatroom"

        # WeFlow API 配置（唯一数据源）
        print()
        print("[WeFlow API 配置]")
        base_url = input("WeFlow服务地址 [http://127.0.0.1:5031]: ").strip() or "http://127.0.0.1:5031"
        config['datasource'] = {
            'type': 'weflow',
            'baseUrl': base_url,
            'chatroomId': config['chatroomId']
        }

        print()
        print("[群成员配置]")
        print("请输入管理者姓名/昵称（用逗号分隔）:")
        managers_input = input("管理者 [管理者A,管理者B,管理者C]: ").strip()
        manager_names = [m.strip() for m in (managers_input or "管理者A,管理者B,管理者C").split(',') if m.strip()]
        config['managers'] = []
        for name in manager_names:
            role = input(f"  {name} 的角色 [管理者]: ").strip() or "管理者"
            config['managers'].append({'name': name, 'role': role})

        print("请输入班长/副班长姓名/昵称（用逗号分隔）:")
        leaders_input = input("班长 [班长A,班长B]: ").strip()
        leader_names = [l.strip() for l in (leaders_input or "班长A,班长B").split(',') if l.strip()]
        config['leaders'] = []
        for name in leader_names:
            role = input(f"  {name} 的角色 [班长]: ").strip() or "班长"
            config['leaders'].append({'name': name, 'role': role})

        # 输出配置
        print()
        print("[输出配置]")
        base_dir = str(self.skill_dir.parent.parent)  # G:\code_library\qunribao
        output_dir = input(f"报告输出目录 [{base_dir}\\reports]: ").strip()
        config['outputDir'] = output_dir or f"{base_dir}\\reports"

        temp_dir = input(f"临时文件目录 [{base_dir}\\temp]: ").strip()
        config['tempDir'] = temp_dir or f"{base_dir}\\temp"

        memory_dir = input(f"记忆文件目录 [{base_dir}\\memory]: ").strip()
        config['memoryDir'] = memory_dir or f"{base_dir}\\memory"

        # 图片识别 API 配置（可选）
        print()
        print("[图片识别 API 配置（可选）]")
        print("describe 模式使用 vision API 分析图片内容。")
        print("留空则使用默认值（智谱 GLM-4.6V-Flash）：")
        has_vision = input("是否配置自定义 vision API? [y/N]: ").strip().lower()
        if has_vision == 'y':
            vision_url = input("  API base URL [https://open.bigmodel.cn/api/paas/v4]: ").strip()
            vision_model = input("  Vision 模型 [glm-4.6v-flash]: ").strip()
            vision_key_env = input("  API Key 环境变量名 [ANTHROPIC_AUTH_TOKEN]: ").strip()
            vision_concurrency = input("  并行数 [10]: ").strip()
            config['vision'] = {
                'baseUrl': vision_url or 'https://open.bigmodel.cn/api/paas/v4',
                'model': vision_model or 'glm-4.6v-flash',
                'apiKeyEnv': vision_key_env or 'ANTHROPIC_AUTH_TOKEN',
                'concurrency': int(vision_concurrency) if vision_concurrency else 10,
            }
        else:
            config['vision'] = None  # 使用脚本内置默认值

        # 使用模板的默认值
        config['valueTopics'] = template.get('valueTopics', [])
        config['engineeringGroups'] = template.get('engineeringGroups', [])

        return config

    def _save_config(self, config: Dict[str, Any]):
        """保存本地配置为 Markdown"""
        ds = config.get('datasource', {})

        lines = []
        lines.append("# qunribao 本地配置")
        lines.append("")
        lines.append("<!-- ⚠️ 本文件包含敏感信息，已被 .gitignore 排除。勿提交到版本控制。 -->")
        lines.append("")
        lines.append("## WeFlow API")
        lines.append(f"- baseUrl: {ds.get('baseUrl', '')}")
        lines.append(f"- chatroomId: {config.get('chatroomId', '')}")
        lines.append("")
        lines.append("## 目录")
        lines.append(f"- outputDir: {config.get('outputDir', '')}")
        lines.append(f"- memoryDir: {config.get('memoryDir', '')}")
        lines.append(f"- tempDir: {config.get('tempDir', '')}")
        lines.append("")
        lines.append("## 人员")
        lines.append("### 管理者/老师")
        for mgr in config.get('managers', []):
            lines.append(f"- {mgr['name']}: {mgr['role']}")
        lines.append("")
        lines.append("### 班长/副班长")
        for ldr in config.get('leaders', []):
            lines.append(f"- {ldr['name']}: {ldr['role']}")
        lines.append("")

        # 图片识别 API
        if config.get('vision'):
            lines.append("## 图片识别 API")
            v = config['vision']
            lines.append(f"- baseUrl: {v['baseUrl']}")
            lines.append(f"- model: {v['model']}")
            lines.append(f"- apiKeyEnv: {v['apiKeyEnv']}")
            lines.append(f"- concurrency: {v['concurrency']}")
            lines.append("")

        lines.append("## 价值议题")
        for topic in config.get('valueTopics', []):
            lines.append(f"- {topic}")
        lines.append("")
        lines.append("## 工程分组")
        for group in config.get('engineeringGroups', []):
            lines.append(f"- {group}")
        lines.append("")

        content = "\n".join(lines)
        with open(self.config_local_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✓ 配置已保存: {self.config_local_path}")

    def _setup_git_hooks(self):
        """设置git hooks"""
        # 项目根目录的 .githooks
        project_root = self.skill_dir.parent.parent.parent  # G:\code_library\qunribao
        hooks_dir = project_root / ".githooks"
        hook_path = hooks_dir / "pre-commit"

        if hook_path.exists():
            print(f"✓ Git hooks 已存在")
            return

        # 创建hooks目录
        hooks_dir.mkdir(exist_ok=True)

        # 创建pre-commit钩子
        hook_content = '''#!/bin/sh
# qunribao pre-commit hook
# 自动检查敏感信息

cd "$(dirname "$0")/.."
python .claude/skills/qunribao/scripts/privacy_scanner.py
'''
        with open(hook_path, 'w', encoding='utf-8') as f:
            f.write(hook_content)

        # 在Windows上也需要使其可执行
        try:
            os.chmod(hook_path, 0o755)
        except Exception:
            pass

        print(f"✓ Git hooks 已设置: {hook_path}")
        print("  提交前将自动检查敏感信息")


def main():
    wizard = InitWizard()
    wizard.run()


if __name__ == '__main__':
    main()
