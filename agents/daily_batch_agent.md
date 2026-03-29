# DailyBatchAgent

## 简介

批量群日报生成 Agent，用于串行生成多天的群日报并更新议题记忆。

## 使用场景

- 批量生成一周日报
- 补生成缺失日期的日报
- 重新生成特定日期范围的日报

## 调用方式

### 作为 SUB Agent 调用

```python
Agent(
    description="DailyBatch-Week",
    prompt="""
你是 DailyBatchAgent，执行批量日报生成。

参数：
- mode: batch
- dateRange: { start: "20260317", end: "20260323" }
- skipResources: true
- skipEngineering: true
- continueOnError: false

对 2026-03-17 至 2026-03-23 共7天，每天串行执行：
1. /qunribao daily --date YYYYMMDD（按下方 skip 规则跳过对应步骤）
2. 验证产出并记录结果
3. 继续下一天

返回每天的结果汇总。
"""
)
```

## 执行流程

```
DailyBatchAgent
│
├── 解析输入参数
│   ├── mode: single | batch
│   ├── date / dateRange
│   └── skipResources, skipEngineering, continueOnError
│
├── 如果 mode == "single"
│   └── 执行 generateDaily(date)
│
├── 如果 mode == "batch"
│   ├── 生成日期列表
│   └── 对每天串行执行 generateDaily(date)
│
└── 返回汇总结果


generateDaily(date) 详细流程：
│
├── Step 1: 执行 Skill
│   └── /qunribao daily --date {date}
│       ├── 若 skipResources=true: 跳过 daily_workflow.md 的 Step 6（不生成资源汇总）
│       └── 若 skipEngineering=true: 跳过 daily_workflow.md 的 Step 7（不生成工程问题归纳）
│
├── Step 2: 验证产出
│   ├── 确认 reports/daily/daily_{date}.md 存在
│   ├── 确认 temp/chat_context_{date}.md 存在
│   └── 确认 memory/topic_tracker_{date}_*.md 已更新
│
└── Step 3: 返回当日结果
```

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | string | 是 | 执行模式：`single` 或 `batch` |
| date | string | 条件 | 单日模式：目标日期 `YYYYMMDD` |
| dateRange | object | 条件 | 批量模式：`{ start, end }` |
| skipResources | boolean | 否 | 跳过资源汇总（跳过 workflow Step 6），默认 `true` |
| skipEngineering | boolean | 否 | 跳过工程问题（跳过 workflow Step 7），默认 `true` |
| continueOnError | boolean | 否 | 出错是否继续，默认 `false` |

## 输出格式

```json
{
  "mode": "single|batch",
  "total": 7,
  "success": 7,
  "failed": 0,
  "results": [
    {
      "date": "20260317",
      "status": "success|failed",
      "dailyReport": "reports/daily/daily_20260317.md",
      "chatContext": "temp/chat_context_20260317.md",
      "memoryFile": "memory/topic_tracker_20260317_121500.md",
      "message": "生成成功|错误信息"
    }
  ]
}
```

## 完整提示词模板

### 单日模式

```markdown
你是 DailyBatchAgent，执行单日日报生成。

## 任务参数
- 模式：single
- 日期：{date}
- 跳过资源汇总：是
- 跳过工程问题：是

## 执行步骤

### Step 1: 生成日报
执行命令：
/qunribao daily --date {date}

**跳过规则**（在执行 daily 流程时遵守）：
- skipResources=true → 跳过 Step 6（资源汇总），不生成文件
- skipEngineering=true → 跳过 Step 7（工程问题），不生成文件

等待命令完成。

### Step 2: 验证产出
确认以下文件存在：
- ✅ reports/daily/daily_{date}.md
- ✅ temp/chat_context_{date}.md
- ✅ memory/topic_tracker_{date}_*.md（记录最新版本）

### Step 3: 返回结果
```json
{
  "date": "{date}",
  "status": "success|failed",
  "dailyReport": "reports/daily/daily_{date}.md",
  "chatContext": "temp/chat_context_{date}.md",
  "memoryFile": "memory/topic_tracker_...",
  "message": "..."
}
```

## 注意事项
- 如执行失败，记录错误信息并返回 failed 状态
- 记忆文件可能有多个版本，记录生成的最新版本
```

### 批量模式

```markdown
你是 DailyBatchAgent，执行批量日报生成。

## 任务参数
- 模式：batch
- 日期范围：{start} 至 {end}
- 跳过资源汇总：是
- 跳过工程问题：是
- 出错继续：false

## 日期列表
{date_list}

## 执行步骤

对每一天按顺序执行：

### 通用流程（每天）
1. 执行 /qunribao daily --date YYYYMMDD
   - 若 skipResources=true：跳过 Step 6（不生成资源汇总）
   - 若 skipEngineering=true：跳过 Step 7（不生成工程问题归纳）
2. 验证产出文件
3. 记录当日结果
4. 继续下一天

## 返回格式
```json
{
  "mode": "batch",
  "total": {total},
  "success": 0,
  "failed": 0,
  "results": [
    {
      "date": "YYYYMMDD",
      "status": "success|failed",
      "dailyReport": "...",
      "chatContext": "...",
      "memoryFile": "...",
      "message": "..."
    }
  ]
}
```

## 注意事项
- 必须串行执行，确保记忆状态正确传递
- skipResources/skipEngineering 是在生成时跳过，不是生成后删除
- 如某天失败且 continueOnError=false，立即中止
- 每天完成后记录结果，最后统一返回
```

## 文件位置

- Agent 定义：`.claude/skills/qunribao/agents/daily_batch_agent.md`

---

*DailyBatchAgent v2.0*
