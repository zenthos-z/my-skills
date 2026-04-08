<div align="center">

# 🧠 Systems Thinking Skill

**Claude Code 的系统思考教练技能**

基于丹尼斯·舍伍德《系统思考》方法论，通过结构化采访帮助你分析复杂问题、
识别反馈回路、找到杠杆解。

[![Skill Type](https://img.shields.io/badge/Type-Claude%20Code%20Skill-blueviolet?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE)
[![Chinese](https://img.shields.io/badge/Language-中文-blue?style=flat-square)](./CLAUDE.md)

[安装](#-安装) · [使用](#-使用) · [流程](#-五阶段采访流程) · [示例](#-真实案例) · [参考](#-参考资源)

</div>

---

## ✨ 它能做什么？

当你面对一个"明明已经解决过却反复出现"的问题时——系统思考能帮你看到隐藏在表面之下的**反馈回路**和**系统结构**。

本技能让 Claude 化身为**采访者而非讲师**，通过提问引导你自己发现：

- 🔄 **反馈回路**：增强回路驱动的增长/衰退，调节回路维持的稳定
- 🔗 **因果结构**：变量间的 S 型（同向）和 O 型（反向）连接
- 🎯 **杠杆解**：与其猛踩油门，不如松开刹车——找到约束并缓和它

## 📦 安装

### 全局安装（所有项目可用）

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/systems-thinking-skill.git

# 复制到 Claude Code 全局技能目录
mkdir -p ~/.claude/skills/systems-thinking
cp -r systems-thinking-skill/{SKILL.md,CLAUDE.md,references,examples} ~/.claude/skills/systems-thinking/
```

### 项目级安装

```bash
# 在你的项目根目录下
mkdir -p .claude/skills/systems-thinking
cp -r systems-thinking-skill/{SKILL.md,CLAUDE.md,references,examples} .claude/skills/systems-thinking/
```

## 🚀 使用

### 直接调用

```
/systems-thinking 我们团队的项目总是延期
```

### 自动激活

当你的提问涉及以下主题时，Claude 会自动使用此技能：

> "帮我分析这个复杂问题"
> "为什么这个问题反复出现？"
> "找出这个系统的反馈回路"
> "帮我画系统循环图"
> "这个问题的杠杆点在哪里？"

## 🔄 五阶段采访流程

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  ① 问题边界探索                                     │
│     核心问题是什么？涉及哪些因素？边界在哪里？        │
│                     ↓                               │
│  ② 因果关系梳理                                     │
│     变量之间如何相互影响？S型还是O型连接？           │
│                     ↓                               │
│  ③ 回路识别                                         │
│     偶数个O → 增强回路(R)  奇数个O → 调节回路(B)    │
│                     ↓                               │
│  ④ 系统循环图绘制                                   │
│     遵循12条黄金法则，整合所有元素                   │
│                     ↓                               │
│  ⑤ 杠杆解识别                                       │
│     找到约束并缓和它——松开刹车而非猛踩油门           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 系统循环图语法

```
[变量A] --S--> [变量B]   同向变化（A↑ → B↑）
[变量A] --O--> [变量B]   反向变化（A↑ → B↓）
[变量A] --S⏳--> [变量B]  存在时滞

R1: [压力] --S--> [加班] --S--> [疲劳] --O--> [效率] --O--> [压力]
    【增强回路 — 恶性循环】
```

## 📋 真实案例

### 员工流失恶性循环

```
R1: [流失率] --S--> [招聘压力] --S--> [入职速度] --O--> [团队稳定性] --O--> [流失率]
    ┗━ 增强回路：流失越快 → 招聘越急 → 质量越低 → 流失越快 ━┛

杠杆解：不是提高薪酬（猛踩油门），而是改善新人融入流程（松开刹车）
```

详见 [`examples/employee-turnover.md`](examples/employee-turnover.md)

### 产品功能蔓延

```
R1: [客户需求] --S--> [功能数量] --S--> [系统复杂度] --S--> [开发周期] --S--> [客户不满] --S--> [客户需求]
R2: [系统复杂度] --S--> [技术债务] --S--> [缺陷率] --S--> [客户不满]
B1: [系统复杂度] --S--> [质量控制] --O--> [发布速度]
```

详见 [`examples/product-feature-creep.md`](examples/product-feature-creep.md)

## 📂 项目结构

```
systems-thinking-skill/
├── SKILL.md                          # 技能定义文件
├── CLAUDE.md                         # Claude Code 上下文指令
├── README.md                         # 本文件
│
├── references/                       # 深度参考文档
│   ├── core-concepts.md              # 核心概念：回路、连接、原型
│   ├── interview-guide.md            # 五阶段详细问题库
│   ├── thinking-tools.md             # 12 种思维分析工具
│   ├── common-pitfalls.md            # 15 个常见陷阱及对策
│   └── output-template.md            # 系统分析报告模板
│
└── examples/                         # 真实案例分析
    ├── employee-turnover.md          # 员工流失恶性循环
    └── product-feature-creep.md      # 产品功能蔓延
```

## 🧰 核心概念速查

| 概念 | 特征 | 行为模式 |
|:-----|:-----|:---------|
| **增强回路 (R)** | 回路中偶数个 O 型连接 | 指数增长或指数衰退 |
| **调节回路 (B)** | 回路中奇数个 O 型连接 | 趋向目标，可能振荡 |
| **S 型连接** | 同向因果关系 | A 增加 → B 增加 |
| **O 型连接** | 反向因果关系 | A 增加 → B 减少 |
| **杠杆解** | 缓和约束而非推动增长 | 最小干预 → 最大效果 |

## ⚠️ 常见思维陷阱

本技能内置了 15 个常见陷阱的识别与应对策略：

| 陷阱 | 症状 | 解药 |
|:-----|:-----|:-----|
| 线性思维 | "多投入就能多产出" | 寻找反馈回路 |
| 忽视时滞 | "为什么还没效果？" | 标注因果链上的延迟 |
| 猛踩油门 | 不断加大干预力度 | 找到并松开刹车 |
| 症状修复 | 反复解决同一个问题 | 追溯根本原因 |
| 静态思维 | 只看当前快照 | 追踪随时间的动态变化 |

详见 [`references/common-pitfalls.md`](references/common-pitfalls.md)

## 📚 参考资源

- **原著**：丹尼斯·舍伍德《系统思考（白金版）》
- **延伸阅读**：彼得·圣吉《第五项修炼》、杰伊·佛睿斯特系统动力学
- **思维工具**：[`references/thinking-tools.md`](references/thinking-tools.md) 包含存量流量分析、心智模式浮现、情景规划等 12 种工具

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](./LICENSE)

---

<div align="center">

**"不要猛踩油门，松开刹车就够了。"**

</div>
