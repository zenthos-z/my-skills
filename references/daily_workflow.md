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

**3c. 分批分配图片分析 Agent**：先读取 `agents/ImageAnalyzer.md` 获取完整的系统提示和描述策略。然后将图片路径列表均分给 4-8 个 general-purpose agent，在同一条消息中并行 spawn 所有 agent（foreground 模式，不使用 `run_in_background`，主会话等待全部完成后继续）。

**分组规则**：
- 总图片数 ≤ 4：每个 agent 1 张，启动 N 个 agent
- 总图片数 5-8：启动 4 个 agent，均分图片
- 总图片数 9-20：启动 4 个 agent，每个处理约 N/4 张
- 总图片数 > 20：启动 6-8 个 agent，每个不超过 5 张

每个 agent 的调用方式：

```
Agent(
  subagent_type="general-purpose",
  description="Analyze batch {N} images",
  prompt="""
{ImageAnalyzer.md 的完整系统提示内容}

---
## 当前任务

batchIndex: {N}
outputDir: {tempDir 的绝对路径}/image_desc_YYYYMMDD
images:
{batch_images_list 的绝对路径}
"""
)
```

其中：
- 系统提示部分：将 `agents/ImageAnalyzer.md` 中 `---` frontmatter 之后的全部正文内容原样嵌入
- **`outputDir` 和 `images` 路径都必须为绝对路径**（如 `G:\code_library\qunribao\temp\image_desc_20260404`），避免 agent 巡作目录与主会话不一致导致文件写入错误位置
- `{batch_images_list}` 是分配给该批次的图片路径，每行一个（保留 `file:///` 前缀）

**3d. 全部 agent 完成后执行替换脚本**：

所有 agent 返回后，确认 `{tempDir}/image_desc_YYYYMMDD/` 下已生成所有 `batch_N.json` 文件，然后执行替换：
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