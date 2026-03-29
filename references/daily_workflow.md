# 日报生成详细流程

本文档描述 `/qunribao daily` 命令的完整执行流程。

## 流程概览

```
Step 1: 加载配置
Step 2: 获取当日聊天数据
Step 3: 预加载图片（有图片时执行）
Step 4: 读取共享内容与记忆文档
Step 5: 生成日报
Step 6: 生成资源汇总
Step 7: 生成工程性问题归纳
Step 8: 更新记忆文档
Step 9: 生成日报配图（可选）
```

---

## Step 1：加载配置

读取本地配置：`assets/config.local.md`（或通过环境变量 `QUNRIBAO_*`），获取：

- `weflow`: WeFlow API 配置（`baseUrl`, `chatroomId`）
- `outputDir`, `memoryDir`, `memoryKeepVersions`: 输出和记忆配置
- `managers`, `leaders`, `valueTopics`: 人员和议题配置
- `imageMode`, `saveChatContext`, `tempDir`: 图片和临时文件配置
- `features.parseLinkCards`: 链接卡片解析开关
- `managerRoles`, `leaderRoles`: 人员角色描述

---

## Step 2：获取当日聊天数据

执行脚本：`scripts/chat_context.py`

```bash
python scripts/chat_context.py --date <YYYY-MM-DD>
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

**两种模式都必须在此步完成图片加载，不可跳过或推迟到分析时。**

### direct 模式

从 Step 2 输出提取所有 `file:///` 开头的行，**在同一条消息中并行发出全部 Read 调用**（单次回复同时调用多个 Read），等所有图片加载完毕后继续。

### describe 模式

**3a. 读取图片路径列表**：读取 `{tempDir}/chat_context_YYYYMMDD_images.txt`（脚本已自动生成，每行一个图片路径）。若该文件不存在或为空，跳过后续 describe 步骤，直接进入 Step 4。

**3b. 创建临时目录**：`{tempDir}/image_desc_YYYYMMDD/`

**3c. 分批分配 subagent**：将图片路径列表均分给 N 个 subagent（每个 subagent 处理约 5 张图片），在同一条消息中并行 spawn 所有 subagent。

每个 subagent 的任务指令：
```
你是一个图片描述生成器。请对以下每张图片调用 `mcp__zai-mcp-server__analyze_image`：
- `image_source`: 本地文件路径（去掉 file:/// 前缀）
- `prompt`: 使用以下分类描述策略：

先判断图片属于哪种类型，再按对应策略描述：

**纯文本截图**（聊天记录、代码、文档、错误信息等）：
逐字还原所有可见文字。如有代码则保留代码格式。标注截图来源（如"VS Code 终端截图"、"微信聊天记录"）。

**操作界面截图**（App 界面、Web 页面、设置面板、工具界面等）：
描述界面布局和主要元素，还原界面中的所有文字内容（按钮、菜单、输入框等）。

**知识卡片 / 信息图**（图文混排的说明图、流程图、思维导图、知识总结等）：
还原所有文字内容，同时说明图片的逻辑结构（如"从左到右分为3个阶段"、"上方是标题，下方是分步骤说明"）。

**海报 / 公告**（活动海报、课程通知、宣传图等）：
还原所有文字内容（标题、时间、地点、联系方式等），简述视觉布局。

**环境照片**（会议室、活动现场、白板、屏幕拍摄等）：
简述环境场景和关键元素，重点提取照片中可见的文字信息。

**表情包 / 梗图**：
简述图片内容和传达的情绪/含义，如有文字则还原。

**其他类型**：
先说明图片性质，再还原关键内容和文字信息。

所有图片可并行调用。

**⚠️ 结果写入方式（必须遵守）**：
不要手写 JSON！所有图片分析完成后，使用 Bash 工具执行 Python 脚本写入 JSON 文件，确保特殊字符被正确转义：

```bash
python -c "
import json, pathlib
data = {
    'file:///path/to/image1.jpg': '图片1的描述',
    'file:///path/to/image2.jpg': '图片2的描述',
}
pathlib.Path('{tempDir}/image_desc_YYYYMMDD/batch_{N}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'写入 {len(data)} 条描述')
"
```

其中 `data` 字典的 key 为 `file:///原始路径`（保留 file:/// 前缀），value 为描述文本。
```

**3d. 等待所有 subagent 完成后执行替换脚本**：
```bash
python scripts/replace_images.py \
  --context {tempDir}/chat_context_YYYYMMDD.md \
  --descriptions-dir {tempDir}/image_desc_YYYYMMDD/
```

**3e. 完成图片预处理**：替换完成后，**不要在此步读取 chat_context**。完整聊天记录将在 Step 5 首次读取，此时 Step 4a 加载的共享内容仍在上下文中，确保日报生成质量。

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

## Step 5：生成日报

**首次读取完整聊天数据**：读取 `{tempDir}/chat_context_YYYYMMDD.md`（describe 模式已被脚本替换为含图片描述的版本）。

读取模板 `.claude/skills/qunribao/references/daily_report.md`，结合已加载的共享内容（Step 4a）和记忆文档（Step 4b），生成结构化日报：

- `direct` 模式：直接引用 Step 3 已加载的图片内容

- `describe` 模式：无需特殊处理，Step 3 已将图片描述插入上下文

输出到 `{outputDir}/daily/群日报 · YYYY-MM-DD.md`。

---

## Step 6：生成资源汇总

输出到 `{outputDir}/resources/群资源 · YYYY-MM-DD.md`。

> **Skip 控制**：批处理模式设置 `skipResources=true` 时跳过此步骤。

---

## Step 7：生成工程性问题归纳

读取模板 `references/engineering_issues.md`，基于当日聊天数据提取工程问题条目，分组按配置中的 `engineeringGroups`。

输出到 `{outputDir}/engineering/工程问题 · YYYY-MM-DD.md`。若当日无工程性内容则跳过（不创建空文件）。

> **Skip 控制**：批处理模式设置 `skipEngineering=true` 时跳过此步骤。

---

## Step 8：更新记忆文档

1. 合并旧记忆 + 当日新结论（格式：`[日期] **背景**：... → **讨论**：... → **结论**：...`）

2. 若 Step 7 有产出（未被跳过），将状态为 ⚠️ / 🔄 的条目（不含 📝）写入记忆文档的 `## 工程待解决问题` 子节，格式见 `references/memory_format.md`

3. 生成记忆文件名：

   从 Step 2 脚本输出中提取 `DATA_END_DATE=YYYYMMDD` 行（若不存在则使用 `--date` 参数日期）。

   执行：
   ```bash
   cd .claude/skills/qunribao && python scripts/memory_filename.py --date <YYYYMMDD>
   ```

   输出即目标文件名（如 `topic_tracker_20260328_000001.md`），写入 `{memoryDir}/<filename>`

4. 清理旧版本：保留最近 `memoryKeepVersions` 个（默认10），删除更早的文件