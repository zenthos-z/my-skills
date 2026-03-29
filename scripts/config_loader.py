"""
多源配置加载器
优先级: 环境变量 > config.local.md
"""

import os
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


class PrivacyError(Exception):
    """配置包含未替换的占位符"""
    pass


class ConfigLoader:
    PLACEHOLDER_PATTERN = re.compile(r'\$\{([^}]+)\}')

    # 当前文件所在目录
    BASE_DIR = Path(__file__).parent.parent
    ASSETS_DIR = BASE_DIR / "assets"

    def __init__(self):
        self._config: Optional[Dict] = None
        self._sources: list = []

    def load(self, validate: bool = True) -> Dict[str, Any]:
        """
        加载配置，按优先级合并
        """
        config = {}

        # 1. 加载 JSON 模板 (最低优先级)
        template_path = self.ASSETS_DIR / "config.json"
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self._sources.append(f"template:{template_path}")

        # 2. 加载 MD 本地配置 (覆盖模板)
        md_path = self.ASSETS_DIR / "config.local.md"
        if md_path.exists():
            md_config = self._parse_md_config(md_path)
            if md_config:
                self._deep_merge(config, md_config)
                self._sources.append(f"local_md:{md_path}")
        else:
            # 回退: 尝试加载 config.local.json (旧格式兼容)
            local_json_path = self.ASSETS_DIR / "config.local.json"
            if local_json_path.exists():
                with open(local_json_path, 'r', encoding='utf-8') as f:
                    local_config = json.load(f)
                self._deep_merge(config, local_config)
                self._sources.append(f"local_json:{local_json_path}")

        # 3. 环境变量 (最高优先级)
        env_config = self._load_from_env()
        if env_config:
            self._deep_merge(config, env_config)
            self._sources.append("environment")

        self._config = config

        if validate:
            self._validate_no_placeholders(config)

        return config

    def _parse_md_config(self, path: Path) -> Dict[str, Any]:
        """
        解析 config.local.md 为 dict

        格式规则:
        - `## Section` → 顶级 key (如 weflow, 目录, 人员)
        - `### SubSection` → 二级 key (如 管理者/老师, 班长/副班长)
        - `- key: value` → 字典条目
        - `- value` → 数组条目
        - `<!-- comment -->` → 忽略
        - `# 标题` → 忽略 (文档标题)
        """
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        config: Dict[str, Any] = {}
        current_section = None
        current_subsection = None

        # Section 名称到 config key 的映射
        section_map = {
            'WeFlow API': 'weflow',
            '目录': 'paths',
            '人员': 'personnel',
            '价值议题': 'valueTopics',
            '工程分组': 'engineeringGroups',
        }

        for line in lines:
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith('<!--') or stripped.startswith('# '):
                # 一级标题是文档标题，忽略；但 ## 是 section
                if stripped.startswith('## '):
                    section_name = stripped[3:].strip()
                    current_section = section_map.get(section_name, section_name)
                    current_subsection = None
                continue

            # ## Section
            if stripped.startswith('## '):
                section_name = stripped[3:].strip()
                current_section = section_map.get(section_name, section_name)
                current_subsection = None
                continue

            # ### SubSection
            if stripped.startswith('### '):
                current_subsection = stripped[4:].strip()
                continue

            # - key: value 或 - value
            if stripped.startswith('- '):
                item = stripped[2:].strip()

                # 解析 key: value 格式
                kv_match = re.match(r'^([^:]+):\s*(.+)$', item)
                if kv_match:
                    key, value = kv_match.group(1).strip(), kv_match.group(2).strip()
                    self._add_md_entry(config, current_section, current_subsection, key, value)
                else:
                    # 纯数组项
                    self._add_md_entry(config, current_section, current_subsection, None, item)

        # 后处理: 将 paths section 展平为顶级 key
        if 'paths' in config:
            for key, value in config.pop('paths').items():
                config[key] = value

        # 后处理: 将 personnel 展平为 managers + leaders + 角色映射
        if 'personnel' in config:
            personnel = config.pop('personnel')
            if '管理者/老师' in personnel:
                entries = personnel['管理者/老师']
                config['managers'] = [e['name'] for e in entries if isinstance(e, dict)]
                config['managerRoles'] = {e['name']: e.get('role', '') for e in entries if isinstance(e, dict)}
            if '班长/副班长' in personnel:
                entries = personnel['班长/副班长']
                config['leaders'] = [e['name'] for e in entries if isinstance(e, dict)]
                config['leaderRoles'] = {e['name']: e.get('role', '') for e in entries if isinstance(e, dict)}

        # 后处理: engineeringGroups 和 valueTopics 从 dict 转为 list
        for key in ['engineeringGroups', 'valueTopics']:
            if key in config and isinstance(config[key], dict):
                config[key] = list(config[key].values())

        return config

    def _add_md_entry(self, config: dict, section: Optional[str],
                      subsection: Optional[str], key: Optional[str], value: str):
        """向 config 结构中添加一个 MD 解析出的条目"""
        if section is None:
            return

        if section not in config:
            config[section] = {}

        target = config[section]

        if subsection:
            if subsection not in target:
                target[subsection] = []
            # subsection 下只有数组项 (人员列表)
            if isinstance(target[subsection], list):
                if key:
                    target[subsection].append({'name': key, 'role': value})
                else:
                    target[subsection].append(value)
        else:
            if key:
                target[key] = value
            else:
                # section 下的数组项 → 转为 dict (用索引作为 key)
                if isinstance(target, dict):
                    idx = len(target)
                    target[str(idx)] = value

    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载，支持嵌套 (QUNRIBAO_WEFLOW_BASEURL)"""
        prefix = "QUNRIBAO_"
        config = {}

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # QUNRIBAO_DATASOURCE_TYPE -> datasource.type
                path = key[len(prefix):].lower().split('_')
                self._set_nested(config, path, value)

        return config

    def _deep_merge(self, base: dict, override: dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _set_nested(self, d: dict, path: list, value: Any):
        """设置嵌套字典值"""
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value

    def _validate_no_placeholders(self, config: dict, path: str = ""):
        """验证配置中无未替换的占位符"""
        for key, value in config.items():
            if key.startswith('_'):
                continue
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, dict):
                self._validate_no_placeholders(value, current_path)
            elif isinstance(value, str):
                matches = self.PLACEHOLDER_PATTERN.findall(value)
                if matches:
                    raise PrivacyError(
                        f"配置项 '{current_path}' 包含未替换的占位符: {matches}\n"
                        f"请设置环境变量或创建 config.local.md"
                    )
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        matches = self.PLACEHOLDER_PATTERN.findall(item)
                        if matches:
                            raise PrivacyError(
                                f"配置项 '{current_path}[{i}]' 包含未替换的占位符: {matches}"
                            )

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号路径 (datasource.type)"""
        if self._config is None:
            self.load()

        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value


# 全局配置实例
_config_loader: Optional[ConfigLoader] = None


def get_config() -> Dict[str, Any]:
    """获取配置单例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.load()


def reload_config() -> Dict[str, Any]:
    """重新加载配置"""
    global _config_loader
    _config_loader = ConfigLoader()
    return _config_loader.load()
