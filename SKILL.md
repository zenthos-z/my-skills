---
name: qunribao
description: |
  群日报生成系统 - 从 WeFlow API 获取微信群聊数据生成多类型报告，支持议题持续追踪。

  Use when:
  - 生成群聊日报/周报
  - 提取群聊资源（需手动修正后使用）
  - 归纳工程性问题
  - 追踪长期议题
  - 将日报转成配图

  Keywords: 日报, 周报, 议题追踪, 资源提取, 工程问题, 记忆机制, 配图
---
# 群日报 (qunribao)

## 核心流程

**执行流程详见：`references/daily_workflow.md`**，单日生成日报比喻按照标准流程生成

## 前置条件

**WeFlow 应用必须已启动并启用 HTTP API 服务**（端口 5031）。

> **唯一数据源**：所有聊天记录均通过 WeFlow API 获取，**禁止使用本地 JSON 文件作为数据源**。若 API 连接失败，需提醒用户开启 WeFlow 并等待重连，不得降级到本地文件。

## 命令

### `/qunribao daily --date <日期>`

生成完整日报。

**执行流程详见：`references/daily_workflow.md`**，单日生成日报比喻按照标准流程生成

**表格行排序**：先输出所有 ⭐ 行，再输出所有 🔄 行，再输出所有 💡 行，最后输出所有 ✅ 行；

### `/qunribao prepare --date <日期>`

仅生成资源提取表格，等待用户手动修正后再执行 `daily`。

### `/qunribao weekly --start <日期> --end <日期>`

生成周报。汇总日期范围内的日报，执行议题归档检查。

### `/qunribao engineering --date <日期>`

生成工程性问题归纳报告。

**手动触发**：

```
用户：将今天的日报转成图片
Claude：读取日报 → 提炼内容 → 调用 dmx-image-gen → 生成配图
```

详见：`references/image_generation.md`

## 配置

配置通过 `scripts/config_loader.py` 加载（优先级：**环境变量 > config.local.md**）：

| 配置项                          | 说明                                        |
| ---------------------------- | ----------------------------------------- |
| `weflow.chatroomId`          | 群聊 ID（如 `12345678@chatroom`）              |
| `weflow.baseUrl`             | WeFlow API 地址（默认 `http://127.0.0.1:5031`） |
| `imageMode`                  | 图片处理：`direct`（嵌入，默认）或 `describe`（MCP 分析 + 脚本替换） |
| `tempDir`                    | 临时文件目录                                    |
| `outputDir`                  | 报告输出目录                                    |
| `memoryDir`                  | 记忆文件目录                                    |
| `managers`                   | 管理者/老师列表（高权重人物）                           |
| `leaders`                    | 班长/副班长列表（高权重人物）                           |
| `valueTopics`                | 价值议题列表                                    |
| `features.parseLinkCards`    | 解析链接卡片（默认 `true`）                         |
| `features.autoGenerateImage` | 自动生成配图（默认 `false`）                        |

**敏感配置推荐环境变量方式**（无需创建 `config.local.md`）：

```bash
export QUNRIBAO_WEFLOW_CHATROOMID="your-chatroom-id@chatroom"
export QUNRIBAO_WEFLOW_BASEURL="http://127.0.0.1:5031"
export QUNRIBAO_OUTPUTDIR="/path/to/reports"
```

格式：`QUNRIBAO_` + 配置路径下划线分隔（如 `weflow.chatroomId` → `QUNRIBAO_WEFLOW_CHATROOMID`）

## 数据获取脚本

聊天上下文生成脚本：`scripts/chat_context.py`

```bash
python scripts/chat_context.py --date 2026-03-25
```

**参数说明**：

- `--date`, `-d`: 目标日期 (YYYY-MM-DD)，默认为今天

- `--start`: 开始时间 (YYYY-MM-DD HH:MM)

- `--end`: 结束时间 (YYYY-MM-DD HH:MM)

- `--sender`: 按发送者名称过滤（模糊匹配）

- `--output`, `-o`: 输出目录

- `--describe`: 使用 describe 模式（输出 `[图片|file:///...]` 占位符，由 `describe_images.py` 并行调用 Vision API 分析后，`replace_images.py` 脚本替换为文字描述）

- `--stats`: 显示统计信息

**注意**：没有 `--inline-images` 参数，默认即嵌入图片模式。如需使用 describe 模式，使用 `--describe`

**输出文件**：`{tempDir}/chat_context_YYYYMMDD.md`

**describe 模式额外输出**：`{tempDir}/chat_context_YYYYMMDD_images.txt`（图片路径列表）
**describe 模式图片分析**：`python scripts/describe_images.py --images-file ... --output-dir ...`（并行 Vision API 分析）

## 记忆机制

议题追踪采用**多版本文件机制**，支持回退到任意历史版本。

**文件命名**：`topic_tracker_YYYYMMDD_VVVVVV.md`
- `YYYYMMDD`：聊天数据中最后一条消息的日期（非当前时间），由 `chat_context.py` 输出 `DATA_END_DATE=`
- `VVVVVV`：当天版本序号（000001, 000002, ...），通过 `scripts/memory_filename.py` 自动生成

**版本保留**：自动保留最近 **10个版本**，生成新版本时自动清理。

**记录规范**：每个结论必须包含 **背景→讨论→结论** 的完整链条。

示例：

```markdown
- [2026-03-18] **背景**：某成员需要提取文献链接 → **讨论**：对比测试OpenClaw和Claude Code → **结论**：OpenClaw更"聪明"（自主使用工具、提供可点击链接）
```

详细格式见：`references/memory_format.md`

## References

| 文件                                  | 内容                 |
| ----------------------------------- | ------------------ |
| `references/daily_workflow.md`      | 日报生成完整流程（Step 1-9） |
| `references/image_generation.md`    | 配图生成配置与使用          |
| `references/daily_report.md`        | 日报提示词模板            |
| `references/weekly_report.md`       | 周报提示词模板            |
| `references/resource_extraction.md` | 资源提取提示词            |
| `references/engineering_issues.md`  | 工程问题提示词            |
| `references/memory_format.md`       | 议题追踪格式规范           |
| `references/shared/topic_hierarchy.md`  | 议题层次定义（⭐🔄💡✅ 四层 + 价值议题说明，gitignored，从模板生成） |
| `references/shared/topic_hierarchy_template.md` | 议题层次通用模板（git-tracked，onboarding 时使用） |
| `references/shared/writing_standards.md` | 结论因果链写作规范（背景→讨论→结论） |
| `references/shared/member_roles.md`     | 群成员分类、关键人物特点、角色标记规则 |
| `references/onboarding_guide.md`        | 首次配置引导流程（对话式初始化） |

## 文件结构

```
.claude/skills/qunribao/
├── scripts/
│   ├── chat_context.py             # [可执行] 聊天上下文生成器
│   ├── config_loader.py            # [核心] 多源配置加载器 (env > local > template)
│   ├── weflow_client.py            # WeFlow API 客户端
│   ├── replace_images.py           # [可执行] 图片描述合并与替换脚本 (describe模式)
│   ├── memory_filename.py          # [可执行] 记忆文件名生成器 (日期+版本序号)
│   ├── init.py                     # [可执行] 初始化向导
│   └── privacy_scanner.py          # [可执行] 隐私扫描器 (pre-commit hook)
├── agents/
│   └── daily_batch_agent.md        # 批量日报生成 Agent
├── references/                     # 提示词模板和流程文档
│   ├── onboarding_guide.md         # 首次配置引导流程
│   └── shared/                     # 共享内容片段（跨步骤复用）
│       ├── topic_hierarchy.md      # 议题层次定义（gitignored，从模板生成）
│       ├── topic_hierarchy_template.md  # 议题层次模板（git-tracked）
│       ├── writing_standards.md    # 结论因果链写作规范
│       └── member_roles.md         # 群成员分类与角色标记
└── assets/
    └── config.local.md             # 本地配置（真实值，gitignored）

reports/
├── daily/                          # 日报输出
├── resources/                      # 资源汇总
├── weekly/                         # 周报输出
└── engineering/                    # 工程问题

memory/
└── topic_tracker_*.md              # 议题追踪记忆（多版本）
```

## 注意事项

- **WeFlow API**：确保 WeFlow 应用已启动并启用 HTTP API（端口 5031）

- **编码**：脚本已处理 Windows 编码，输出 UTF-8