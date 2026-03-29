# 初始化引导流程

> 本文件指导 Claude 在用户首次使用 qunribao 或配置缺失时，通过对话交互完成配置初始化。

---

## 触发条件

以下任一情况触发本引导：
- 用户说"初始化配置"、"设置 qunribao"、"第一次用"等
- `assets/config.local.md` 不存在
- 执行命令时 `config_loader.py` 报 `PrivacyError`（占位符未替换）

---

## 引导原则

1. **分阶段提问**，每阶段最多 1-2 个问题，不要一次列出所有配置项
2. **能选不填**：能用选择题的就用选择题，减少用户输入负担
3. **有默认值就提供**：让用户只需确认或选择"使用默认值"
4. **及时反馈**：每个阶段完成后告知用户进度（如"第 2/4 步"）
5. **最后统一确认**：收集完毕后展示配置摘要，用户确认后写入文件

---

## 引导流程

### 前置检查

开始前先检查以下文件状态：
- `assets/config.local.md` 是否已存在
- `references/shared/topic_hierarchy.md` 是否已存在

```
if config.local.md 存在:
    AskUserQuestion: "检测到已有配置文件，你想？"
    选项: [查看当前配置] / [重新配置（覆盖）] / [取消]
    → 选"查看"则 Read 文件并展示，然后结束
    → 选"重新配置"则继续下面的流程
    → 选"取消"则结束
else:
    直接进入 Step 1
```

---

### Step 1/5：群聊连接

> 这是唯一必须手动提供信息的步骤。

```
AskUserQuestion (2 questions):
  Q1: "群聊 ID 是什么？"
      格式提示: "在 WeFlow 中打开目标群聊，群 ID 格式如 123456789@chatroom"
      类型: 填空题（用户自由输入）

  Q2: "WeFlow API 地址？"
      选项:
        - "http://127.0.0.1:5031（本地默认）" ← 大多数情况选这个
        - "自定义地址"
      类型: 选择题
      → 选"自定义地址"时追问具体地址
```

**收集结果**：
- `chatroomId`: Q1 的输入
- `baseUrl`: Q2 选择的地址（默认 `http://127.0.0.1:5031`）

---

### Step 2/5：人员配置

> 人员信息影响报告中的权重标注和角色标记。

```
AskUserQuestion (1 question):
  Q1: "是否需要配置高权重人员？"
      选项:
        - "需要配置" → 展开子问题
        - "暂时跳过（后续可在 config.local.md 中补充）"
      类型: 选择题

  → 如果选"需要配置":

  AskUserQuestion (2 questions):
    Q2: "管理者/老师（项目核心人物，观点需高权重标注），请输入姓名，逗号分隔："
        示例提示: "如：张三,李四"
        类型: 填空题

    Q3: "班长/副班长（项目组织协调），请输入姓名，逗号分隔："
        示例提示: "如：王五,赵六"
        类型: 填空题

  → 如果提供了管理者名单:
  AskUserQuestion (1 question):
    Q4: "请为管理者补充角色描述（可跳过）"
        格式: "姓名→角色，如：张三→项目发起人，李四→技术指导"
        类型: 填空题（可留空）

  → 如果提供了班长名单:
  AskUserQuestion (1 question):
    Q5: "请为班长补充角色描述（可跳过）"
        格式: 同上
        类型: 填空题（可留空）
```

**收集结果**：
- `managers`: `[{name: "张三", role: "项目发起人"}, ...]`
- `leaders`: `[{name: "王五", role: "班长"}, ...]`

---

### Step 3/5：输出目录

```
AskUserQuestion (1 question):
  Q1: "报告和文件存放在哪里？"
      选项:
        - "使用默认目录（项目根目录下的 reports/、memory/、temp/）" ← 推荐
        - "自定义路径"
      类型: 选择题

  → 如果选"自定义路径":
  AskUserQuestion (1 question):
    Q2: "请输入报告输出目录的绝对路径："
        示例提示: "如 G:\my_reports 或 /home/user/reports"
        类型: 填空题
        （memory 和 temp 目录自动在同级创建）
```

**收集结果**：
- `outputDir`: 用户路径或 `{projectRoot}/reports`
- `memoryDir`: 用户路径或 `{projectRoot}/memory`
- `tempDir`: 用户路径或 `{projectRoot}/temp`

---

### Step 4/5：议题列表配置

```
AskUserQuestion (1 question):
  Q1: "价值议题和工程分组如何设置？"
      选项:
        - "使用默认模板（Agentic/AI 项目通用）" ← 推荐
        - "自定义议题"
      类型: 选择题

  → 如果选"自定义议题":
  AskUserQuestion (1 question):
    Q2: "请输入价值议题，逗号分隔："
        示例提示: "如：任务编排,记忆机制,强化学习"
        类型: 填空题
        （工程分组也一并追问）
```

**默认议题模板**：
```markdown
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

---

### Step 4b/5：议题知识库配置

> 这一步是日报生成质量的关键。`topic_hierarchy.md` 定义了每个价值议题的核心内容、常见误区和最佳实践，
> Claude 在生成日报时会据此判断和归类讨论内容。如果不填写，日报的议题标注将缺乏深度。

先告知用户：
```
💡 议题知识库说明

日报生成时，Claude 会根据「议题知识库」来判断和归类群聊中的讨论内容。
每个价值议题需要填写三个维度：

1. 核心内容 — 这个议题讨论什么、有哪些关键概念
2. 关键痛点/误区 — 群成员常犯的错误或误解
3. 核心要求/建议 — 群内共识或最佳实践

以下是一个已填好的示例：

### 记忆机制
- 核心内容
  1. 将知识、经验、规则外显为结构化文件，支持持续读写和迁移
  2. 记忆分类：绘画记忆、任务记忆、工序状态记忆、策略记忆
- 关键痛点/误区
  1. 虚假记忆：口头答应记住，未实际写入文件
  2. 无差别记忆导致冗余噪声，拖慢系统
- 核心要求/建议
  1. 满足外显化、可验证，手动验证文件修改与规则落实
  2. 高频复用内容沉淀为长期记忆，临时内容仅保留在上下文
```

```
AskUserQuestion (1 question):
  Q1: "是否现在为每个议题填写详细描述？"
      选项:
        - "我现在逐一填写" ← 推荐，日报质量更高
        - "先跳过，稍后手动编辑"
      类型: 选择题
```

→ 如果选"我现在逐一填写":

对 Step 4a 中确定的每个价值议题，逐个收集三个维度：
```
AskUserQuestion (3 questions):
  Q_核心: "{议题名称} 的核心内容是什么？（这个议题讨论什么、有哪些关键概念）"
      类型: 填空题

  Q_痛点: "{议题名称} 的常见痛点/误区？（群成员常犯的错误或误解）"
      类型: 填空题

  Q_建议: "{议题名称} 的核心要求/建议？（群内共识或最佳实践）"
      类型: 填空题
```

每个议题收集完成后立即追加到 `topic_hierarchy.md` 草稿中。
所有议题收集完毕后，写入 `references/shared/topic_hierarchy.md`。

→ 如果选"先跳过，稍后手动编辑":

从模板复制创建空结构：
```
将 references/shared/topic_hierarchy_template.md 复制为 references/shared/topic_hierarchy.md
告知用户：
"已创建空模板文件。后续请编辑 references/shared/topic_hierarchy.md 补充每个议题的详细描述。
这是日报生成质量的直接决定因素。"
```

---

### Step 4c/5：其他共享文件说明

简短告知用户，不需要交互操作：

```
📝 其他共享文件说明（无需立即操作）：

- member_roles.md — 人员分类规则，通用不需要修改（人名从 config 读取）
- writing_standards.md — 结论写作规范，格式通用，示例中的群特定内容可后续更新

这些文件位于 references/shared/ 目录，可随时编辑。
```

---

## 确认与写入

所有步骤完成后，展示配置摘要并确认：

```
展示给用户:

"配置确认，请检查以下信息："

| 项目 | 值 |
|------|-----|
| 群聊 ID | 123456789@chatroom |
| API 地址 | http://127.0.0.1:5031 |
| 管理者 | 张三（项目发起人）、李四（技术指导） |
| 班长 | 王五（班长） |
| 报告目录 | G:\code_library\qunribao\reports |
| 议题 | 使用默认模板 |
| 议题知识库 | ✅ 已填写 / ⚠️ 空模板待补充 |

⚠️ 共享文件状态：
- references/shared/topic_hierarchy.md: ✅ 已生成 / ⚠️ 空模板，需手动补充议题详细描述
- references/shared/member_roles.md: 通用，无需修改
- references/shared/writing_standards.md: 通用，示例可后续更新

AskUserQuestion:
  "确认写入配置？"
  选项:
    - "确认，写入配置" → 写入文件
    - "需要修改" → 询问修改哪项，返回对应步骤
    - "取消" → 放弃
```

用户确认后，将配置写入 `assets/config.local.md`，格式如下：

```markdown
# qunribao 本地配置

<!-- ⚠️ 本文件包含敏感信息，已被 .gitignore 排除。勿提交到版本控制。 -->

## WeFlow API
- baseUrl: {baseUrl}
- chatroomId: {chatroomId}

## 目录
- outputDir: {outputDir}
- memoryDir: {memoryDir}
- tempDir: {tempDir}

## 人员
### 管理者/老师
- {name}: {role}
...

### 班长/副班长
- {name}: {role}
...

## 价值议题
- {topic}
...

## 工程分组
- {group}
...
```

写入后告知用户：

```
配置已保存到 assets/config.local.md

接下来可以：
- 生成日报：对我说 "/qunribao daily --date 今天日期"
- 查看完整文档：阅读 README.md

⚠️ 如果你跳过了议题知识库配置：
- 编辑 references/shared/topic_hierarchy.md，为每个议题补充核心内容/痛点/建议
- 这是日报生成质量的直接决定因素

提示：如需修改配置，随时对我说"修改配置"，或直接编辑 assets/config.local.md
```

---

## 后续修改引导

用户说"修改配置"时：

```
AskUserQuestion:
  "要修改哪项配置？"
  选项:
    - "群聊连接（群ID / API地址）"
    - "人员名单（管理者 / 班长）"
    - "输出目录"
    - "议题配置"
    - "查看当前配置"
```

选择后，Read 当前 `config.local.md`，进入对应步骤重新收集，最后覆写整个文件。
