<p align="center">
  <img src="https://img.shields.io/badge/Claude%20Code-Skills%20Monorepo-blue?logo=claude" alt="Claude Code Skills">
  <img src="https://img.shields.io/badge/skills-4-green" alt="Skills Count">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

<h1 align="center">my-skills</h1>

<p align="center"><b>Claude Code 技能仓库 — 为 Claude 注入领域专属能力</b></p>

<p align="center">
  <a href="./README.md">English</a> | <b>中文</b>
</p>

---

## TL;DR

**痛点：** Claude Code 功能强大，但重复性任务（图表生成、报告撰写、图片创建、结构化分析）每次都需要手动构造提示词。

**方案：** 可安装的技能包，教会 Claude 领域专属工作流 — 内置语法校验、结构化输出和多步骤自动化。

| 技能 | 一句话描述 | 运行时 |
|------|-----------|--------|
| [mermaid-pro](./mermaid-pro/) | Mermaid 图表生成 + 语法校验 + 图片导出 | Node.js |
| [systems-thinking](./systems-thinking/) | 结构化系统思考访谈，支持会话持久化 | 无 |
| [qunribao](./qunribao/) | 微信群聊日报/周报自动生成 | Python |
| [quick-img](./quick-img/) | 通过 DMX API 快速生图（Gemini Flash） | Python |

## 快速开始

```bash
# 安装单个技能
npx skills add zenthos-z/my-skills/mermaid-pro

# 或安装全部技能
npx skills add zenthos-z/my-skills/mermaid-pro
npx skills add zenthos-z/my-skills/systems-thinking
npx skills add zenthos-z/my-skills/qunribao
npx skills add zenthos-z/my-skills/quick-img
```

安装后，技能会在 Claude Code 中自动激活 — 触发对应关键词即可（如"生成 mermaid 图"、"系统思考访谈"、"群日报"）。

## 技能概览

### mermaid-pro

专业 Mermaid 图表生成，统一的视觉风格。

- **9色语义调色板** — 按含义着色（绿色=开始，红色=判断，蓝色=流程）
- **内置语法校验** — 每张图表在输出前均经过解析和验证
- **批量图片导出** — 将 Markdown 文件中所有 Mermaid 代码块转为 SVG/PNG
- **7种图表类型** — 流程图、时序图、类图、ER图、C4架构图、状态图、思维导图
- **3种风格预设** — minimal、professional（默认）、colorful
- **完全离线** — 无外部 API 调用，Puppeteer 本地渲染

```bash
# 安装后初始化
cd ~/.claude/skills/mermaid-pro/scripts && npm install
```

详见 [mermaid-pro/README.md](./mermaid-pro/)。

---

### systems-thinking

基于 Dennis Sherwood 方法论的结构化系统思考教练。

- **5阶段访谈协议** — Claude 引导你完成问题边界探索、因果映射、回路识别、图示绘制和杠杆点发现
- **会话持久化** — 每阶段自动保存进度，可跨对话恢复
- **15种思维陷阱识别** — 捕捉线性思维、治标不治本、忽略时延等问题
- **系统回路图语法** — 文本标记 `[A] --S--> [B]`（同向）、`[A] --O--> [B]`（反向）
- **零依赖** — 纯提示词工程，无需运行时环境

无需安装配置，直接调用即可开始访谈。

---

### qunribao

微信群日报/周报自动生成系统。

- **JSON 优先架构** — 结构化 JSON → JSON Schema 校验 → Markdown 表格
- **记忆机制** — 多版本议题追踪，自动清理（保留最近10个版本）
- **描述模式** — 用 Vision API 分析聊天图片，替代不可靠的文件路径
- **飞书多维表格上传** — 直接构造 JSON → Bitable 负载
- **隐私扫描器** — pre-commit 钩子检测群 ID、API 密钥、手机号
- **优雅降级** — 未安装 `quick-img` 时仍可正常工作

```bash
# 需要 Python 3.8+ 及运行中的 WeFlow 实例（端口 5031）
# 首次设置：在 Claude Code 中运行初始化向导
```

详见 [qunribao/README.md](./qunribao/)。

---

### quick-img

通过 DMX API（Gemini 3.1 Flash Image Preview）快速生图。

- **3种使用模式** — 直接提示词、模板模式（Markdown → 信息图）、精炼模式（浓缩 → 确认 → 生成）
- **14种宽高比** — 社交媒体（4:5）、演示文稿（16:9）、手机（9:16）等
- **4档分辨率** — 0.5K 快速预览到 4K 印刷品质
- **批量"抽卡"模式** — 同一提示词，利用 API 随机性生成多张不同结果
- **思源笔记集成** — 读取思源笔记内容作为生图提示词
- **模板系统** — 自定义 `.txt` 模板，使用 `{{content}}` 占位符

```bash
# 需要 Python 3.8+ 和 DMX API 密钥
# 在 assets/.env 中设置密钥：DMX_API_KEY=sk-...
```

详见 [quick-img/README.md](./quick-img/)。

## 技能间依赖

```mermaid
graph LR
    qunribao -->|可选封面图| quick-img
```

| 技能 | 依赖 | 是否必须 |
|------|------|----------|
| qunribao | quick-img | 否 — 未安装时优雅降级 |

其余技能完全独立。

## 安装方式

### 方式一：npx skills add（推荐）

```bash
npx skills add zenthos-z/my-skills/<技能名>
```

### 方式二：手动复制

```bash
# 复制单个技能
cp -r mermaid-pro ~/.claude/skills/

# 复制全部技能
cp -r mermaid-pro systems-thinking qunribao quick-img ~/.claude/skills/
```

### 方式三：克隆仓库

```bash
git clone https://github.com/zenthos-z/my-skills.git
# 然后将所需技能复制到 ~/.claude/skills/
```

## 环境要求

| 技能 | 运行时 | 外部服务 |
|------|--------|----------|
| mermaid-pro | Node.js >= 18 | 无（完全离线） |
| systems-thinking | 无 | 无 |
| qunribao | Python 3.8+ | WeFlow（本地，端口 5031） |
| quick-img | Python 3.8+ | DMX API（云端） |

## 贡献

欢迎贡献。每个技能自包含 — 可自由添加新技能或改进现有技能。

## 许可证

所有技能基于 MIT 许可证发布。详见各技能目录。
