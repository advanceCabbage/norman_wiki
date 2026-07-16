# Superpowers 与 grilling 源码对比：如何约束 Agent 的规划流程

## 一、grilling：用极简规则锁定规划节奏

> GitHub 地址：[https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

```text
---
name: grilling

description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.(就计划、决策或想法对用户进行无情盘问。适用于用户想要测试其思维能力，或使用任何“盘问”触发词的情况)
---

Interview me relentlessly about every aspect of this until we reach a shared understanding. Walk down each branch of the decision tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.(就此计划的各个方面对我进行无情盘问，直到我们达成共识。沿着决策树的每个分支逐一分析，逐一解决决策之间的依赖关系。对于每个问题，请提供您的建议答案)

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.(一次只问一个问题，并在获得每个问题的反馈后再继续。同时提出多个问题会令用户感到困惑)

If a *fact* can be found by exploring the environment (filesystem, tools, etc.), look it up rather than asking me. The *decisions*, though, are mine — put each one to me and wait for my answer.(如果某个*事实*可以通过探索环境（文件系统、工具等）找到，请自行查找，而不是问我。但是，*决策*由我决定——请将每个决策都告诉我，并等待我的答复)

Do not act on it until I confirm we have reached a shared understanding.(在我确认我们已达成共识之前，请勿采取任何行动)
```

## 二、Superpowers：用多层护栏固化规划流程

> brainstorming 的核心内容记录在 `SKILL.md` 中。由于整篇内容过长，这里只分析其中的精华。GitHub 地址：[https://github.com/obra/superpowers](https://github.com/obra/superpowers)

### 2.1 Frontmatter

```yaml
---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.（在进行任何创造性工作（如创建特性、构建组件、增加功能或修改行为）之前，**必须**使用此流程。它旨在实施前深入探讨用户意图、需求及设计方案。）"
---
```

**优势：** `description` 是唯一决定这个 skill 会不会被自动触发的字段。用 "MUST" 这种祈使语气而非中性描述，是为了在触发阈值上占优。与其让模型自行判断“要不要用”，不如把义务直接写进描述本身，提高命中率。

### 2.2 开篇定调

```text
Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.（通过自然流畅的协作对话，帮助将想法转化为完整的设计方案和规范。首先了解当前项目背景，然后逐一提出问题，逐步完善想法。一旦明确了要构建的内容，即可展示设计方案并获得用户认可。）
```

**优势：** 一句话定基调（对话协作，不是审讯表单）；第二段把全流程压缩预告成一句“电梯摘要”，后面章节都是对它的展开。

### 2.3 `<HARD-GATE>`

```text
<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>（<HARD-GATE>
在提交设计方案并获得用户批准之前，严禁进行任何具体实现、编写代码、搭建项目框架或采取任何实施行动。此规定适用于所有项目，无论其看起来多么简单。
</HARD-GATE>）
```

**优势：** 用非标准伪 XML 标签制造“这是特殊级别规则”的视觉信号。内容直接禁止最常见的失败模式：跳过设计，直接写代码。

### 2.4 反例补充

```text
## Anti-Pattern: "This Is Too Simple To Need A Design"
Every project goes through this process. A todo list, a single-function utility, a config change — all of them.（反模式：“这太简单了，无需设计”。
每个项目都会经历这一过程。无论是待办事项列表、单一功能的实用工具，还是配置变更——无一例外。）
```

**优势：** 不是重复规则，而是提前堵死为违反规则辩护的理由。专门列出反例（todo list、单函数工具），把“这次真的很简单”这个借口打掉。

### 2.5 Checklist

```text
You MUST create a task for each of these items and complete them in order:
1. Explore project context
...
2. Transition to implementation
```

**优势：** 和 TaskCreate 工具绑定，强制把每一步显式化，跳步就无法悄悄隐藏。

### 2.6 Process Flow / dot 状态图

```text
"User approves design?" -> "Present design sections" [label="no, revise"];
"User reviews spec?" -> "Write design doc" [label="changes requested"];
```

**优势：** 形式化图表把两个审批回路表达得毫无歧义，比纯文字更难被曲解成“单向走一遍就行”。

### 2.7 "The Process" 详述

- **规模评估先于提问**（第 68-69 行）：多子系统项目要先拆解，避免在错误颗粒度上浪费提问。
- **一次一问、优先选择题**（第 70-72 行）：降低用户认知负担，加快收敛。

### 2.8 Key Principles

```text
- One question at a time （每次只关注一个问题）
- Multiple choice preferred （优先采用多项选择方案）
- YAGNI ruthlessly （严格遵循 YAGNI 原则（非必要不构建））
- Explore alternatives （探索多种备选方案）
- Incremental validation （循序渐进地进行验证）
- Be flexible （保持灵活性）
```

**优势：** 全文摘要卡片，用更精炼的措辞把分散规则再讲一遍，类似“间隔重复”。尤其在长对话被压缩摘要后，这段精炼版更容易被保留。

## 三、汇总：规划类 skill 的核心是加护栏

Superpower 和 grilling 都不是在教模型“怎么问问题”，而是在对抗模型最容易走的捷径：跳过设计、替用户做决定、未经确认就执行。

grilling 用极短规则锁住“一次一问、事实自查、确认后行动”；Superpower 则用 HARD-GATE、反例、checklist、状态图和关键原则重复，让同一套约束更显眼、更难被跳过。

写这类 skill 时，重点是明确不可跳过的门槛、真实的审批点和步骤状态。复杂流程可借鉴 Superpower 的多层约束；简单场景则可以像 grilling 一样，只保留最关键的几条规则。
