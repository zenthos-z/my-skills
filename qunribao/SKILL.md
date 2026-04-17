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

**任务配置记忆**：每次执行时自动检测 `config.local.md` 中的 `## 上次任务` section，询问是否沿用上次步骤配置（资源提取、工程问题、飞书上传、配图），只需提供新日期。重置方法：编辑 `config.local.md`，删除 `## 上次任务` section。

### `/qunribao prepare --date <日期>`

仅生成资源提取表格，等待用户手动修正后再执行 `daily`。

### `/qunribao weekly --start <日期> --end <日期>`

生成周报。汇总日期范围内的日报，执行议题归档检查。

### `/qunribao engineering --date <日期>`

生成工程性问题归纳报告。

**手动触发**：

```
用户：将今天的日报转成图片
Claude：读取日报 → 提炼内容 → 检查 quick-img 技能 → 调用生图
```

**配图依赖**：配图功能依赖独立的 `quick-img` 技能（https://github.com/zenthos-z/quick-img）。

- 若 quick-img 已安装：直接调用 `generate_image.py` 生图（见 `daily_workflow.md` Step 9）
- 若 quick-img 未安装：向用户说明并询问是否安装，安装命令为 `npx skills add zenthos-z/my-skills/quick-img`
- 若用户拒绝安装：停止配图步骤，等待用户指定替代方案

配图流程：
1. Claude 读取 `assets/templates/日报配图提炼.md` 内联精炼日报内容
2. `scripts/assemble_image_json.py` 组装 JSON（自动读取风格指南路径和默认配置）
3. 通过 Skill 工具调用 quick-img，传入 JSON 文件路径
4. quick-img 读取 JSON → 追加风格 → 调 API 生图

配图模板文件位于 `assets/templates/` 目录：
- `日报配图提炼.md` - 日报内容提炼提示词（认知洞察和行动信息同等重要）
- `日报生图风格.md` - 配图视觉风格定义（通过 JSON `style_guide` 字段传递给 quick-img）

## 配置

配置通过 `scripts/config_loader.py` 加载（优先级：**环境变量 > config.local.md**）：

| 配置项                          | 说明                                        |
| ---------------------------- | ----------------------------------------- |
| `weflow.chatroomId`          | 群聊 ID（如 `12345678@chatroom`）              |
| `weflow.token`               | API 鉴权 Token（WeFlow 强制要求）              |
| `weflow.baseUrl`             | WeFlow API 地址（默认 `http://127.0.0.1:5031`） |
| `imageMode`                  | 图片处理：`describe`（默认，Vision API 分析）或 `direct`（嵌入，不可靠） |
| `tempDir`                    | 临时文件目录                                    |
| `outputDir`                  | 报告输出目录                                    |
| `memoryDir`                  | 记忆文件目录                                    |
| `managers`                   | 管理者/老师列表（高权重人物）                           |
| `leaders`                    | 班长/副班长列表（高权重人物）                           |
| `valueTopics`                | 价值议题列表                                    |
| `features.parseLinkCards`    | 解析链接卡片（默认 `true`）                         |
| `features.autoGenerateImage` | 自动生成配图（默认 `false`）                        |
| `feishu.upload`              | 是否上传到飞书（默认 `false`）                    |
| `feishu.bitableAppToken`     | 飞书多维表格 App Token                        |
| `feishu.resourceTableId`     | 资源表 ID                                  |
| `feishu.engineeringTableId`  | 工程问题表 ID                              |
| `feishu.identity`            | 飞书身份标识（如 `bot`）                          |

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

- `--direct`: 使用 direct 模式（嵌入图片为 `file:///` 路径，不可靠，模型无法实际看到图片内容）

- `--stats`: 显示统计信息

**注意**：默认即为 describe 模式（图片占位符 + Vision API 分析）。如需 direct 模式，使用 `--direct`（不推荐）

**输出文件**：`{tempDir}/chat_context_YYYYMMDD.md`

**describe 模式额外输出**：`{tempDir}/chat_context_YYYYMMDD_images.txt`（图片路径列表）
**describe 模式图片分析**：`python scripts/describe_images.py --images-file ... --output-dir ...`（并行 Vision API 分析）

## JSON 中间产物架构

报告生成采用 **JSON 优先** 架构：

1. **Step 5-7**：主 Agent 生成结构化 JSON 数据
   - 日报：`{outputDir}/daily/群日报 · YYYY-MM-DD.json`
   - 资源：`{outputDir}/resources/群资源 · YYYY-MM-DD.json`
   - 工程问题：`{outputDir}/engineering/工程问题 · YYYY-MM-DD.json`

2. **Step 5.1-7.1**：Subagent 使用 `scripts/json_validator.py` 验证并修正 JSON

3. **Step 5.2-7.2**：使用 `scripts/json_to_md.py` 转换为 Markdown 表格

4. **Step 8**：使用 `scripts/feishu_upload.py` 从 JSON 直接构建飞书上传 payload

**CHECKPOINT**：Step 8 在上传前会展示预览，等待用户确认后再执行 lark-cli 命令。

**依赖安装**：需要 `jsonschema` 库：
```bash
pip install jsonschema
```

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

## 任务配置记忆

系统自动记录上次成功执行的任务步骤配置，保存在 `config.local.md` 的 `## 上次任务` section。

**工作流程**：
1. 执行 `/qunribao daily --date <日期>` 时，首先检查 `lastTask` 配置
2. 如有历史配置，展示摘要并询问是否沿用（用户可沿用或自定义）
3. 确认后立即保存本次配置（不等到流程结束）

**config.local.md 格式**：
```markdown
## 上次任务
- lastRun: 2026-04-09T14:30:00+08:00
- lastDate: 2026-04-08
- command: daily
- resource: true
- engineering: true
- feishuUpload: true
- generateImage: true
- imageCount: 3
- imageRatio: 4:5
- imageSize: 2K
```

**重置**：编辑 `config.local.md`，删除 `## 上次任务` section 即可恢复首次运行行为。

## References

| 文件                                  | 内容                 |
| ----------------------------------- | ------------------ |
| `references/daily_workflow.md`      | 日报生成完整流程 |
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
qunribao/
├── scripts/
│   ├── chat_context.py             # [可执行] 聊天上下文生成器
│   ├── config_loader.py            # [核心] 多源配置加载器 (env > local > template)
│   ├── weflow_client.py            # WeFlow API 客户端
│   ├── replace_images.py           # [可执行] 图片描述合并与替换脚本 (describe模式)
│   ├── memory_filename.py          # [可执行] 记忆文件名生成器 (日期+版本序号)
│   ├── init.py                     # [可执行] 初始化向导
│   ├── json_validator.py           # [可执行] JSON Schema 质量检测（Subagent专用）
│   ├── json_to_md.py               # [可执行] JSON → Markdown 表格转换
│   └── feishu_upload.py            # [可执行] 飞书上传准备（JSON→Bitable payload）
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
    ├── config.local.md             # 本地配置（真实值，gitignored）
    └── templates/                  # 配图模板文件
        ├── 日报配图提炼.md         # 配图内容提炼提示词
        ├── 认知日报提炼.md         # 认知型日报配图提炼
        └── 日报生图风格.md         # 配图视觉风格定义

reports/
├── daily/                          # 日报输出
│   └── 群日报 · YYYY-MM-DD.md     # Markdown 报告
├── resources/                      # 资源汇总
│   └── 群资源 · YYYY-MM-DD.md
├── weekly/                         # 周报输出
├── engineering/                    # 工程问题
│   └── 工程问题 · YYYY-MM-DD.md
└── json/                           # JSON 中间产物（永久保留）
    ├── 群日报 · YYYY-MM-DD.json
    ├── 群资源 · YYYY-MM-DD.json
    └── 工程问题 · YYYY-MM-DD.json

memory/
└── topic_tracker_*.md              # 议题追踪记忆（多版本）
```

## 注意事项

- **WeFlow API**：确保 WeFlow 应用已启动并启用 HTTP API（端口 5031）

- **编码**：脚本已处理 Windows 编码，输出 UTF-8