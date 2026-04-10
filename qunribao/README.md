# qunribao

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/code)

从微信群聊数据自动生成日报、周报、资源汇总和议题追踪报告。基于 WeFlow API 获取聊天数据，Claude 完成分析和报告生成。

核心能力：日报 / 周报 / 资源提取 / 工程问题归纳 / 议题持续追踪 / 配图生成


![日报_20260329_194756_02](https://github.com/user-attachments/assets/a071cb17-1250-4b30-80c2-35faa74dae38)


## 安装

### 一键安装（推荐）

```bash
npx skills add zenthos-z/my-skills/qunribao
```

> 支持所有主流 AI 编程助手：Claude Code、Cursor、Codex、Cline、Roo Code 等 40+ 客户端。
> 详见 [skills CLI](https://github.com/vercel-labs/skills)。

```bash
# 指定安装到 Claude Code
npx skills add zenthos-z/my-skills/qunribao -a claude-code

# 全局安装（所有项目可用）
npx skills add zenthos-z/my-skills/qunribao -g

# 指定安装到多个客户端
npx skills add zenthos-z/my-skills/qunribao -a claude-code -a cursor -a codex
```

### 手动安装

```bash
# 从 monorepo 克隆（推荐）
git clone https://github.com/zenthos-z/my-skills.git

# 安装到项目
mkdir -p .claude/skills
cp -r my-skills/qunribao .claude/skills/
```

安装后在 Claude Code 中即可通过 `/qunribao` 使用。详见下方配置说明。

---

## 前置条件

1. **WeFlow 应用已启动**，HTTP API 服务开启（默认端口 5031）
2. Python 3.8+ + `requests` 库
3. 微信群聊 ID（格式如 `123456789@chatroom`，从 WeFlow 获取）

---

## 快速初始化

需要配置 3 类信息：**群聊连接**、**人员名单**、**输出路径**。提供 3 种方式：

### 方式 A：AI 对话引导（推荐）

在 Claude Code 中直接说"初始化配置"或"帮我配置 qunribao"，Claude 会按 `references/onboarding_guide.md` 定义的流程分步引导：

1. **群聊连接**（填空）：群 ID、API 地址
2. **人员配置**（填空+选择）：管理者/班长姓名和角色，或选择跳过
3. **输出目录**（选择）：使用默认目录或自定义
4. **议题配置**（选择）：使用默认模板或自定义

每步都有选择题辅助，减少输入负担。收集完毕后展示摘要确认，然后写入 `config.local.md`。

### 方式 B：环境变量（最快，适合临时使用）

```bash
# 必须配置
export QUNRIBAO_WEFLOW_CHATROOMID="你的群ID@chatroom"
export QUNRIBAO_WEFLOW_BASEURL="http://127.0.0.1:5031"
export QUNRIBAO_OUTPUTDIR="/path/to/reports"
export QUNRIBAO_TEMPDIR="/path/to/temp"
export QUNRIBAO_MEMORYDIR="/path/to/memory"

# 可选：人员配置
export QUNRIBAO_MANAGERS="张三:项目发起人,李四:指导老师"
export QUNRIBAO_LEADERS="王五:班长"
```

格式规则：`QUNRIBAO_` + 配置路径下划线分隔大写（如 `weflow.chatroomId` → `QUNRIBAO_WEFLOW_CHATROOMID`）。

### 方式 C：手动编辑

创建 `assets/config.local.md`，填入真实值：

```markdown
# qunribao 本地配置

<!-- ⚠️ 本文件包含敏感信息，已被 .gitignore 排除。勿提交到版本控制。 -->

## WeFlow API
- baseUrl: http://127.0.0.1:5031
- chatroomId: YOUR_CHATROOM_ID@chatroom

## 目录
- outputDir: /path/to/reports
- memoryDir: /path/to/memory
- tempDir: /path/to/temp

## 人员
### 管理者/老师
- 姓名: 角色描述

### 班长/副班长
- 姓名: 角色描述

## 价值议题
- 强制隔离下的任务编排
- 约束工程 & Harness Engineering
- 记忆机制
- 世界模型
- 强化学习
- 可视化调试

## 工程分组
- 部署与基础设施
- 开发与调试工具
- 记忆与进化机制
- 生态与工具链
- 成本控制与性能优化
- 安全与合规
```

### 配置优先级

```
环境变量 QUNRIBAO_*  >  config.local.md
```

| 配置项 | 环境变量 | config.local.md 中的键 |
|--------|----------|----------------------|
| 群聊 ID | `QUNRIBAO_WEFLOW_CHATROOMID` | `WeFlow API → chatroomId` |
| API 地址 | `QUNRIBAO_WEFLOW_BASEURL` | `WeFlow API → baseUrl` |
| 报告输出 | `QUNRIBAO_OUTPUTDIR` | `目录 → outputDir` |
| 管理者 | `QUNRIBAO_MANAGERS` | `人员 → 管理者/老师` |
| 班长 | `QUNRIBAO_LEADERS` | `人员 → 班长/副班长` |

`config_loader.py` 统一处理三级合并，Python 脚本和 Claude 读取同一份配置。

---

## 获取聊天记录

### 数据来源

**WeFlow** 是本地运行的微信数据提取工具，通过 HTTP API（端口 5031）提供群聊消息。

### 核心脚本：chat_context.py

```bash
# 获取某天的聊天记录
python scripts/chat_context.py --date 2026-03-29

# 指定时间范围
python scripts/chat_context.py --start "2026-03-29 09:00" --end "2026-03-29 18:00"

# 按发送者过滤
python scripts/chat_context.py --date 2026-03-29 --sender 张三

# describe 模式（不嵌入图片，改为文字描述）
python scripts/chat_context.py --date 2026-03-29 --describe

# 显示统计信息
python scripts/chat_context.py --date 2026-03-29 --stats
```

**输出文件**：`{tempDir}/chat_context_YYYYMMDD.md` — 格式化的聊天记录，图片以 `file:///` 路径嵌入。

### WeFlow API 方法

通过 `weflow_client.py` 提供的 API 客户端：

| 方法 | 说明 |
|------|------|
| `health_check()` | 检查 WeFlow 连接是否正常 |
| `get_messages(chatroom_id, start, end)` | 获取消息（支持时间范围、分页、关键词过滤） |
| `get_all_messages(chatroom_id, start, end)` | 自动分页获取全部消息 |
| `get_group_members(chatroom_id)` | 获取群成员列表及昵称 |
| `download_media(url, path)` | 下载图片/文件等媒体资源 |

### 消息解析能力

`weflow_client.py` 能解析微信的原始 XML 消息格式：

- **引用消息**：提取被引用的消息内容和发送者
- **链接卡片**：识别公众号文章、外部链接、小程序
- **文件分享**：提取文件名、大小、类型
- **图片/视频/语音**：自动处理媒体路径

---

## 上下文组装机制

Claude 执行日报/周报生成时，按以下顺序加载信息：

```
Step 1:   config.local.md          ← 敏感信息（群ID、人名、路径）
    ↓
Step 2-3: 聊天数据 + 图片         ← chat_context.py 输出
    ↓
Step 4a:  references/shared/*.md   ← 共享内容（议题层次、写作规范、角色规则）
    ↓
Step 4b:  记忆文档                 ← topic_tracker_*.md（历史议题追踪）
    ↓
Step 5+: 生成报告
```

### 三层信息分工

| 层 | 文件位置 | 内容 | git 状态 |
|----|----------|------|----------|
| **敏感信息** | `assets/config.local.md` | 群ID、人名+角色、本地路径 | gitignored |
| **共享内容** | `references/shared/*.md` | 议题层次、写作规范、角色规则（3 个文件） | tracked |
| **模板逻辑** | `references/*.md` | 各报告的独特格式、流程、提示词 | tracked |

**设计原则**：敏感信息集中在一个文件（gitignored），共享内容定义一次多处引用，模板只保留自身独特逻辑。

### 共享内容文件

| 文件 | 内容 | 被引用于 |
|------|------|----------|
| `shared/topic_hierarchy.md` | ⭐🔄💡✅ 四层议题定义 + 6 个价值议题 | 日报、周报、记忆格式 |
| `shared/writing_standards.md` | 结论因果链规范（背景→讨论→结论） | 日报、记忆格式 |
| `shared/member_roles.md` | 成员分类 + 角色标记规则 | 日报、周报、记忆格式 |

---

## 目录结构

```
（安装后的路径：~/.claude/skills/qunribao/）
├── README.md                       ← 本文件
├── SKILL.md                        ← Claude skill 注册信息
├── scripts/
│   ├── chat_context.py             ← 聊天数据获取 + 文档生成
│   ├── config_loader.py            ← 配置加载器
│   ├── weflow_client.py            ← WeFlow API 客户端
│   ├── init.py                     ← CLI 初始化向导
│   └── privacy_scanner.py          ← 隐私扫描（pre-commit hook）
├── assets/
│   └── config.local.md             ← 本地配置（gitignored，需手动创建）
├── references/                     ← 报告模板和流程文档
│   ├── onboarding_guide.md         ← 首次配置引导流程（对话式）
│   ├── daily_workflow.md           ← 日报完整流程（Step 1-9）
│   ├── daily_report.md             ← 日报提示词模板
│   ├── weekly_report.md            ← 周报提示词模板
│   ├── resource_extraction.md      ← 资源提取提示词
│   ├── engineering_issues.md       ← 工程问题提示词
│   ├── memory_format.md            ← 议题追踪格式规范
│   └── shared/                     ← 跨模板共享内容
│       ├── topic_hierarchy.md      ← 议题层次定义
│       ├── writing_standards.md    ← 写作规范
│       └── member_roles.md         ← 成员角色规则
└── agents/
    └── daily_batch_agent.md        ← 批量日报生成 Agent

reports/                            ← 报告输出（项目根目录下）
├── daily/                          ← 日报
├── weekly/                         ← 周报
├── resources/                      ← 资源汇总
├── engineering/                    ← 工程问题报告
└── images/                         ← 图片描述（describe 模式）

memory/                             ← 议题追踪（多版本，保留最近 10 个）
└── topic_tracker_YYYYMMDD_HHMMSS.md
```

---

## 隐私保护

- `config.local.md` 被 `.gitignore` 排除，不会提交到版本控制
- `privacy_scanner.py` 作为 pre-commit hook 自动扫描敏感信息（群ID、API 密钥、路径、电话号码）
- `config_loader.py` 在加载时验证无未替换的占位符，发现则抛出 `PrivacyError`

配置完成后可安全分享整个项目——所有敏感信息都在 gitignored 文件中。
