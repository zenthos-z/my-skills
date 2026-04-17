# 日报生成详细流程

本文档描述 `/qunribao daily` 命令的完整执行流程。

## 流程概览

```
Step 0: 加载并确认任务配置 → 保存到 config.local.md
Step 1: 加载配置
Step 2: 获取当日聊天数据
Step 3: 预加载图片（有图片时执行）
Step 4: 读取共享内容与记忆文档
Step 5: 生成日报 JSON 数据
Step 6: 生成资源 JSON 数据
Step 7: 生成工程问题 JSON 数据
Step 8: 飞书上传
Step 9: 更新记忆文档
Step 10: 生成日报配图（可选）
```

---

## Step 0：加载并确认任务配置

> 在 Step 1 之前执行。**确认后立即保存**到 config.local.md，不等到流程结束。

### 0a. 检查上次任务配置

读取 `config.local.md` 中的 `## 上次任务` section（通过 config_loader 解析为 `config['lastTask']`）。

**若 `lastTask` 不存在或为空**（首次运行）：
- 设定 `runSteps` 默认值：`resource=true`、`engineering=true`、`feishuUpload=true`、`generateImage=true`
- **立即保存**到 config.local.md（追加 `## 上次任务` section）
- 进入 Step 1

**若 `lastTask` 存在**：

向用户展示上次配置摘要：

```
📋 检测到上次日报任务配置（{lastTask.lastRun}，数据日期 {lastTask.lastDate}）：

| 步骤 | 状态 |
|------|------|
| 资源提取 (Step 6) | {lastTask.resource == 'true' ? '✅ 执行' : '⏭️ 跳过'} |
| 工程问题 (Step 7) | {lastTask.engineering == 'true' ? '✅ 执行' : '⏭️ 跳过'} |
| 飞书上传 (Step 8) | {lastTask.feishuUpload == 'true' ? '✅ 执行' : '⏭️ 跳过'} |
| 生成配图 (Step 10) | {lastTask.generateImage == 'true' ? '✅ 执行' : '⏭️ 跳过'} |

是否沿用上次配置？只需提供新日期。
```

用户选择：
- **沿用上次配置** → 从 `lastTask` 读取步骤开关，设置 `runSteps`
- **自定义本次配置** → 逐一询问每个可选步骤是否执行，设置 `runSteps`

### 0b. 保存任务配置

**确认后立即保存**（不等到流程结束），使用 Edit 工具更新 `assets/config.local.md` 的 `## 上次任务` section：

```markdown
## 上次任务
- lastRun: {当前时间 ISO 8601}
- lastDate: {--date 参数值}
- command: daily
- resource: {runSteps.resource}
- engineering: {runSteps.engineering}
- feishuUpload: {runSteps.feishuUpload}
- generateImage: {runSteps.generateImage}
- imageCount: 3
- imageRatio: 4:5
- imageSize: 2K
```

若 section 不存在，追加到文件末尾。若已存在，替换整个 section 内容。

### 0c. 记录 runSteps 到上下文

将以下参数记录到上下文，供后续步骤条件判断：
- `runSteps.resource`：是否执行 Step 6
- `runSteps.engineering`：是否执行 Step 7
- `runSteps.feishuUpload`：是否执行 Step 8（需同时满足配置 `feishu.upload=true`）
- `runSteps.generateImage`：是否执行 Step 10

---

## Step 1：加载配置

读取本地配置：`assets/config.local.md`（或通过环境变量 `QUNRIBAO_*`），获取：

- `weflow`: WeFlow API 配置（`baseUrl`, `chatroomId`）
- `outputDir`, `memoryDir`, `memoryKeepVersions`: 输出和记忆配置
- `managers`, `leaders`, `valueTopics`: 人员和议题配置
- `imageMode`, `saveChatContext`, `tempDir`: 图片和临时文件配置
- `features.parseLinkCards`: 链接卡片解析开关
- `managerRoles`, `leaderRoles`: 人员角色描述
- `feishu`: 飞书配置（`upload`, `bitableAppToken`, `resourceTableId`, `engineeringTableId`, `identity`）

---

## Step 2：获取当日聊天数据

执行脚本：`scripts/chat_context.py`

```bash
# 默认即为 describe 模式（图片占位符 + 路径列表）
python scripts/chat_context.py --date <YYYY-MM-DD>
# 如需 direct 模式（不可靠，图片以 file:// 嵌入）：加 --direct
```

参数详见：`SKILL.md` → 数据获取脚本

**WeFlow API 连接失败处理**：若脚本输出 `❌ WeFlow API 连接失败`，**不可使用本地 JSON 文件作为替代数据源**。必须：

1. 向用户说明：「WeFlow API 连接失败（端口 5031），请确认 WeFlow 应用已启动并启用 HTTP API 服务。」
2. 等待用户确认已开启 WeFlow
3. 重新执行脚本获取数据
4. 重复直到连接成功

**输出文件**：`{tempDir}/chat_context_YYYYMMDD.md`

---

## Step 3：预加载图片（有图片时执行）

**默认使用 describe 模式。两种模式都必须在此步完成图片加载，不可跳过或推迟到分析时。**

### describe 模式（默认）

**3a. 读取图片路径列表**：读取 `{tempDir}/chat_context_YYYYMMDD_images.txt`（脚本已自动生成，每行一个图片路径）。若该文件不存在或为空，跳过后续 describe 步骤，直接进入 Step 4。

**3b. 执行图片分析脚本**：

```bash
python scripts/describe_images.py \
  --images-file {tempDir}/chat_context_YYYYMMDD_images.txt \
  --output-dir {tempDir}/image_desc_YYYYMMDD
```

脚本内部自动：
- base64 编码每张图片
- 并行调用 vision API（并发 ≥ 10，asyncio.Semaphore 控制）
- 失败重试（最多 3 次，指数退避）
- 输出 descriptions.json + 统计信息

**3c. 检查退出码和统计输出**：
- 退出码 0 + 有成功描述：继续
- 退出码 1：全部失败，向用户报告错误

**3d. 执行替换**：
```bash
python scripts/replace_images.py \
  --context {tempDir}/chat_context_YYYYMMDD.md \
  --descriptions-dir {tempDir}/image_desc_YYYYMMDD/
```

**3e. 完成图片预处理**：替换完成后，**不要在此步读取 chat_context**。完整聊天记录将在 Step 5 首次读取，此时 Step 4a 加载的共享内容仍在上下文中，确保日报生成质量。

### direct 模式（备选，需在 Step 2 加 `--direct`）

> ⚠️ direct 模式不可靠：Read 工具将图片上传到 CDN 返回 URL，模型无法实际看到图片内容。仅在确信环境支持时使用。

从 Step 2 输出提取所有 `file:///` 开头的行，**在同一条消息中并行发出全部 Read 调用**（单次回复同时调用多个 Read），等所有图片加载完毕后继续。

---

## Step 4：读取共享内容与记忆文档

### Step 4a：读取共享内容片段

依次读取以下文件，后续步骤中直接引用这些已加载的内容：

- `references/shared/topic_hierarchy.md`：议题层次定义（⭐🔄💡✅ 四层 + 价值议题详细说明）
- `references/shared/writing_standards.md`：结论因果链写作规范（背景→讨论→结论，含错误/正确示例）
- `references/shared/member_roles.md`：群成员分类、关键人物特点、角色标记规则

**Fallback**：若 `topic_hierarchy.md` 不存在，说明用户未完成初始化配置：
1. 检查 `references/shared/topic_hierarchy_template.md` 是否存在
2. 向用户说明：「议题知识库文件不存在，日报的议题标注将无法进行。请先运行初始化配置，或手动从模板创建。」
3. 等待用户确认后再继续（此时日报生成将缺少议题分类能力）

> 以上内容在 Step 4a 加载后，后续步骤中提到的"共享内容"均指这些已加载的片段。

### Step 4b：读取记忆文档

扫描 `memoryDir`，列出所有 `topic_tracker_*.md` 文件，按文件名排序后读取最新版本，提取未完成议题和历史结论。

---

## Step 5：生成日报 JSON 数据

**首次读取完整聊天数据**：读取 `{tempDir}/chat_context_YYYYMMDD.md`（describe 模式已被脚本替换为含图片描述的版本）。

> **已有数据**：若目标 JSON 文件已存在，暂停并询问用户是否覆盖。用户选择复用则跳过生成，直接进入 Step 5.1 验证已有数据；用户确认覆盖后，**必须先用 Read 读取已有文件**（Claude Code 安全机制要求先读后写），再用 Write 覆盖写入新内容。

结合已加载的共享内容（Step 4a）和记忆文档（Step 4b），生成结构化日报 JSON：

```json
{
  "type": "daily",
  "date": "2026-04-08",
  "alerts": ["❗️重要提醒内容"],
  "topics": [
    {
      "time": "2026-04-08 09:35",
      "level": "⭐",
      "content": "议题标题",
      "progress": "进度描述",
      "conclusion": "背景→讨论→结论",
      "participants": ["成员1", "成员2"]
    }
  ],
  "trends": {
    "phase_features": ["特征1"],
    "open_issues": ["问题1"]
  },
  "active_members": ["成员1", "成员2"]
}
```

输出到 `{outputDir}/json/群日报 · YYYY-MM-DD.json`。

### Step 5.1：验证并修正 JSON（Subagent）

启动 Subagent 执行格式检测和修正：

```bash
python scripts/json_validator.py --daily <json_path> --fix
```

Subagent 循环执行以下操作：
1. 读取 JSON 文件
2. 调用 json_validator.py 验证：
   - Schema 验证（字段名、类型、必填项、枚举值）
   - 格式验证（日期格式 `YYYY-MM-DD HH:MM`、emoji 枚举）
   - 排序验证（topics 按 `⭐ > 🔄 > 💡 > ✅`）
3. 若有问题，Subagent 修正并写回文件，然后重测
4. 通过后，Subagent 返回纯净 JSON 内容给主 agent

### Step 5.2：生成完整日报 MD

1. 执行 `json_to_md.py --input <json_path> --output <table_md>` 生成表格部分

   > **注意**：脚本输出路径中含中文文件名时，控制台显示可能乱码（`Ⱥ�ձ�`），但实际文件写入正确，不影响后续步骤。可忽略。

2. 主 agent 读取表格 + chat_context + 共享内容，补充以下自由文本段落：
   - 概览（当日讨论主题、重要议题）
   - 讨论趋势（phase_features、open_issues）
   - 活跃成员（active_members）
3. 输出完整日报 MD 到 `{outputDir}/daily/群日报 · YYYY-MM-DD.md`

---

## Step 6：生成资源 JSON 数据

> **执行条件**：`runSteps.resource=true` 时执行此步骤。若 `runSteps.resource=false`，跳过 Step 6、6.1、6.2。

基于当日聊天数据提取资源条目，生成结构化资源 JSON：

> **已有数据**：若目标 JSON 文件已存在，暂停并询问用户是否覆盖。用户选择复用则跳过生成，直接进入 Step 6.1 验证已有数据；用户确认覆盖后，**必须先用 Read 读取已有文件**（Claude Code 安全机制要求先读后写），再用 Write 覆盖写入新内容。

```json
{
  "type": "resource",
  "date_range": ["2026-04-06", "2026-04-08"],
  "resources": [
    {
      "time": "2026-04-08 06:39",
      "title": "资源标题",
      "type": "链接",
      "summary": "资源简介",
      "content": "https://...",
      "shared_by": "分享人"
    }
  ]
}
```

输出到 `{outputDir}/json/群资源 · YYYY-MM-DD.json`。

### Step 6.1：验证并修正 JSON（Subagent）

```bash
python scripts/json_validator.py --resource <json_path> --fix
```

Subagent 验证并修正后返回纯净 JSON。

### Step 6.2：生成资源 MD

```bash
python scripts/json_to_md.py --input <json_path> --output <md_path>
```

输出到 `{outputDir}/resources/群资源 · YYYY-MM-DD.md`。

> **Skip 控制**：批处理模式设置 `skipResources=true` 时跳过此步骤。

---

## Step 7：生成工程问题 JSON 数据

> **执行条件**：`runSteps.engineering=true` 时执行此步骤。若 `runSteps.engineering=false`，跳过 Step 7、7.1、7.2。

基于当日聊天数据提取工程问题条目，按配置中的 `engineeringGroups` 分组，生成结构化 JSON：

> **已有数据**：若目标 JSON 文件已存在，暂停并询问用户是否覆盖。用户选择复用则跳过生成，直接进入 Step 7.1 验证已有数据；用户确认覆盖后，**必须先用 Read 读取已有文件**（Claude Code 安全机制要求先读后写），再用 Write 覆盖写入新内容。

```json
{
  "type": "engineering",
  "date_range": ["2026-04-06", "2026-04-08"],
  "issues": [
    {
      "datetime": "2026-04-08 14:24",
      "group": "开发与调试工具",
      "description": "问题描述",
      "solution": "解决方案",
      "tools": "关键操作/工具",
      "status": "🔄",
      "status_desc": "方案待验证",
      "source": "成员1、成员2"
    }
  ]
}
```

输出到 `{outputDir}/json/工程问题 · YYYY-MM-DD.json`。若当日无工程性内容则跳过（不创建空文件）。

### Step 7.1：验证并修正 JSON（Subagent）

```bash
python scripts/json_validator.py --engineering <json_path> --fix
```

Subagent 验证并修正后返回纯净 JSON。

### Step 7.2：生成工程问题 MD

```bash
python scripts/json_to_md.py --input <json_path> --output <md_path>
```

输出到 `{outputDir}/engineering/工程问题 · YYYY-MM-DD.md`。

> **Skip 控制**：批处理模式设置 `skipEngineering=true` 时跳过此步骤。

---

## Step 8：飞书上传

### Step 8.1：构建上传 payload

```bash
python scripts/feishu_upload.py \
  --resource-json <resource_json_path> \
  --engineering-json <engineering_json_path> \
  --config <config.local.md path>
```

脚本从 JSON 文件直接构建 Bitable 记录 payload，生成 `lark-cli api POST` 命令。

### Step 8.2：CHECKPOINT — 确认上传

**必须展示每条待上传记录的完整内容**，供用户逐一审阅，而非仅展示数量或摘要。

展示格式：

**资源表（{count} 条）**：
| # | 发布日期 | 资源标题 | 标签 | 简介 | 具体内容 | 分享人 |
|---|---------|---------|------|------|---------|--------|
| 1 | 2026-04-08 09:35 | 完整标题 | 链接 | 完整简介 | 完整URL | 张三 |
| ... | ... | ... | ... | ... | ... | ... |

**工程问题表（{count} 条）**：
| # | 日期 | 问题分组 | 问题描述 | 解决方案 | 关键操作/工具 | 状态 | 状态描述 | 信息来源 |
|---|------|---------|---------|---------|-------------|------|---------|---------|
| 1 | 2026-04-08 14:24 | 开发与调试工具 | 完整描述 | 完整方案 | 完整操作 | 🔄 | 方案待验证 | 成员1 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

**要求**：
- 每个字段展示**完整内容**，不截断、不省略
- 若内容过长（如具体内容含长URL），使用换行展示，不折叠
- 用户审阅后确认上传，或指出需要修改的条目

用户确认后执行 lark-cli 命令上传到飞书多维表格。

> **注意**：`feishu_upload.py` 生成的命令可能包含 `--id` 参数，但 `lark-cli api` 子命令不支持此参数。若执行报错 `unknown flag: --id`，移除该参数后重试。

> **Skip 控制**：需同时满足 `feishu.upload=true`（系统配置）且 `runSteps.feishuUpload=true`（任务配置）。任一为 false 则跳过。

---

## Step 9：更新记忆文档

1. 合并旧记忆 + 当日新结论（格式：`[日期] **背景**：... → **讨论**：... → **结论**：...`）

2. 若 Step 7 有产出（未被跳过），将状态为 ⚠️ / 🔄 的条目（不含 📝）写入记忆文档的 `## 工程待解决问题` 子节，格式见 `references/memory_format.md`

3. 生成记忆文件名：

   从 Step 2 脚本输出中提取 `DATA_END_DATE=YYYYMMDD` 行（若不存在则使用 `--date` 参数日期）。

   执行：
   ```bash
   python scripts/memory_filename.py --date <YYYYMMDD>
   ```

   输出即目标文件名（如 `topic_tracker_20260328_000001.md`），写入 `{memoryDir}/<filename>`

4. 清理旧版本：保留最近 `memoryKeepVersions` 个（默认10），删除更早的文件

---

## Step 10：生成日报配图（可选）

> **执行条件**：`runSteps.generateImage=true` 时执行此步骤。首次运行时，若用户未明确要求配图，设为 false。
>
> 若 `features.autoGenerateImage=true` 且 `runSteps.generateImage` 未明确设置，默认执行。

### 10a：检查 quick-img 技能

检测 quick-img 技能是否可用：
1. 检查已加载的技能列表中是否包含 `quick-img`
2. 或检查已安装的 `quick-img` 技能中 `scripts/generate_image.py` 是否存在

**若 quick-img 不可用**：
1. 停止配图步骤
2. 告知用户：「配图功能需要 quick-img 技能，当前未检测到。是否立即安装？」
3. 用户同意 → 执行：`npx skills add zenthos-z/my-skills/quick-img`
4. 用户拒绝 → 停止，等待用户指定替代方案。**不得自行选择替代方案**

### 10b：提炼配图内容

使用 `assets/templates/日报配图提炼.md` 模板提炼日报核心内容。
Claude 读取提炼模板，按其指引内联精炼日报内容。认知洞察和行动信息同等重要，都应保留。

**提炼要求**：
- 提炼内容控制在原文 15%-25%
- 保留核心议题标题和结论
- 保留关键数据和活跃成员列表
- 不含风格指令，风格由 `--style-guide` 参数传递

### 10c：组装 JSON 并调用 quick-img 生图

**Step 1：组装 JSON 配置**

使用 `scripts/assemble_image_json.py` 脚本组装 JSON：

```bash
python scripts/assemble_image_json.py \
  --prompt "{提炼后的精简内容}" \
  --date {date} \
  --count {imageCount}
```

脚本自动完成：
- 读取 `assets/templates/日报生图风格.md` 路径填入 `style_guide` 字段
- 读取 config 中的默认 `ratio`、`size`、`output_dir`
- CLI 参数覆盖默认值（`--count`、`--ratio`、`--size`）
- 输出 JSON 文件路径到 stdout

**Step 2：调起 quick-img 技能**

```
Skill(skill: "quick-img", args: "<脚本输出的JSON文件路径>")
```

quick-img 加载后，Claude 直接透传给脚本：
```bash
python scripts/generate_image.py --json <JSON文件路径>
```

**参数说明**：
- `{imageCount}` 张图使用完全相同的提示词，供用户挑选最佳一张
- 比例和分辨率由任务配置决定（默认 4:5 / 2K）
- 风格由 `日报生图风格.md` 控制，通过 JSON 的 `style_guide` 字段传递
