## 一、知名博主对比文章
卡颂：https://x.com/kasong2048/status/2074449455122960448

#### 1.1 需求收集部分差异
grill-me 起源于作者 @mattpocockuk 作为程序员的自用 skill 合集，这意味着 grill-me 带有大量作者个人风格。Matt 是优秀的开发者，所以 grill-me 的假设是：**你的脑海里已有方案，只是缺少细节**，这意味着，如果你只有一个念头，且在交流时只能被动 接受或拒绝 AI 的建议，那你就会被问非常多的问题。
正确做法：
- 交流前就有个主干
- 主动引导对话，一次对话长更多树枝
- 用/prototype 等工具的产出给他额外的信息


Superpowers 的 brainstorming **假设是你只有模糊的想法，agent 就你的想法给你指方向**

#### 1. 2 后续执行流程差异
- grill-me 由于问得非常全面，后续流程做得很轻量，只有在代码完成后有一个 review 流程。
- SuperPowers 在生成需求文档、需求文档转执行计划，以及计划执行的过程中，都会派出多个 Reviewer。他们不仅把控代码质量，还会补齐很多缺失的需求细节。这也导致很多人诟病 Swift Power 执行时间太长，太费 token

#### 1.3 各自的实现原理

**Superpowers 输出详细执行计划**，这意味着他隐含的假设是：

- Agent 无法执行长程任务，所以需要 Plan 的 TODO 作为 Compact 后的执行锚点

- Agent 长程执行会有偏差，所以执行计划需要细致到“每一步做啥”

**grill-me 的 implement 就 5 句话**，定义了一个标准的 Goal 格式：

- 目标是什么：去查 PRD 或 issue
    
- 怎么做：TDD
    
- 执行约束：定期执行测试和类型检查
    
- 通过标准：使用 /review 验收通过
    
- 交付标准：提交 commit


## 二、对比 superPower 和 grilling skill 源码

#### 2.1 grilling 源码展示
> github 地址:https://github.com/mattpocock/skills

```
---
name: grilling

description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.(就计划、决策或想法对用户进行无情盘问。适用于用户想要测试其思维能力，或使用任何“盘问”触发词的情况)
---

Interview me relentlessly about every aspect of this until we reach a shared understanding. Walk down each branch of the decision tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.(就此计划的各个方面对我进行无情盘问，直到我们达成共识。沿着决策树的每个分支逐一分析，逐一解决决策之间的依赖关系。对于每个问题，请提供您的建议答案)

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.(一次只问一个问题，并在获得每个问题的反馈后再继续。同时提出多个问题会令用户感到困惑)

If a *fact* can be found by exploring the environment (filesystem, tools, etc.), look it up rather than asking me. The *decisions*, though, are mine — put each one to me and wait for my answer.(如果某个*事实*可以通过探索环境（文件系统、工具等）找到，请自行查找，而不是问我。但是，*决策*由我决定——请将每个决策都告诉我，并等待我的答复)

Do not act on it until I confirm we have reached a shared understanding.(在我确认我们已达成共识之前，请勿采取任何行动)
```
#### 2.2 superPower brainstorming 源码分析
> brainstorming 的核心内容记录在 SKILL.md 中，由于整篇内容过长，这里就分析 SKILL 中的精华。github 地址：https://github.com/obra/superpowers
##### 2.2.1  Frontmatter
```
---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.（在进行任何创造性工作（如创建特性、构建组件、增加功能或修改行为）之前，**必须**使用此流程。它旨在实施前深入探讨用户意图、需求及设计方案。）"
---
```
**好处：** `description` 是唯一决定这个 skill 会不会被自动触发的字段。用"MUST"这种祈使语气而非中性描述，是为了在触发阈值上占优——与其让模型自行判断"要不要用"，不如把义务直接写进描述本身，提高命中率
##### 2.2.2 开篇定调
```
Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.（通过自然流畅的协作对话，帮助将想法转化为完整的设计方案和规范。首先了解当前项目背景，然后逐一提出问题，逐步完善想法。一旦明确了要构建的内容，即可展示设计方案并获得用户认可。）
```
**好处：** 一句话定基调（对话协作，不是审讯表单），第二段把全流程压缩预告成一句"电梯摘要"，后面章节都是对它的展开
##### 2.2.3  `<HARD-GATE>`
```
<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>（<HARD-GATE>
在提交设计方案并获得用户批准之前，严禁进行任何具体实现、编写代码、搭建项目框架或采取任何实施行动。此规定适用于所有项目，无论其看起来多么简单。
</HARD-GATE>）
```
**好处：** **用非标准伪 XML 标签制造"这是特殊级别规则"的视觉信号**。内容直接禁止最常见的失败模式——跳过设计直接写代码。
##### 2.2.4 反例补充
```
## Anti-Pattern: "This Is Too Simple To Need A Design"
Every project goes through this process. A todo list, a single-function utility, a config change — all of them.(反模式：“这太简单了，无需设计”
每个项目都会经历这一过程。无论是待办事项列表、单一功能的实用工具，还是配置变更——无一例外)
```
**好处：** 不是重复规则，而是**提前堵死为违反规则辩护的理由**，专门列反例（todo list、单函数工具）把"这次真的很简单"这个借口打掉
##### 2.2.5 Checklist
```
You MUST create a task for each of these items and complete them in order:
1. Explore project context
...
2. Transition to implementation
```
**好处：** 和 TaskCreate 工具绑定，强制把每一步显式化，跳步就无法悄悄隐藏
##### 2.2.6 Process Flow / dot 状态图
```
"User approves design?" -> "Present design sections" [label="no, revise"];
"User reviews spec?" -> "Write design doc" [label="changes requested"];
```
**好处：** 形式化图表把两个审批回路表达得毫无歧义，比纯文字更难被曲解成"单向走一遍就行"
##### 2.2.7 "The Process" 详述
- **规模评估先于提问**（第 68-69 行）：多子系统项目要先拆解，避免在错误颗粒度上浪费提问。
- **一次一问、优先选择题**（第 70-72 行）：降低用户认知负担，加快收敛。
##### 2.2.8 Key Principles

```
- One question at a time （每次只关注一个问题）
- Multiple choice preferred （优先采用多项选择方案）
- YAGNI ruthlessly （严格遵循 YAGNI 原则（非必要不构建））
- Explore alternatives （探索多种备选方案）
- Incremental validation （循序渐进地进行验证）
- Be flexible （保持灵活性）
```
**好处：** 全文摘要卡片，用更精炼的措辞把分散规则再讲一遍——类似"间隔重复"，尤其在长对话被压缩摘要后，这段精炼版更容易被保留。

### 2.3 汇总：规划类 skill 的核心是加护栏

Superpower 和 grilling 都不是在教模型“怎么问问题”，而是在对抗模型最容易走的捷径：跳过设计、替用户做决定、未经确认就执行。

grilling 用极短规则锁住“一次一问、事实自查、确认后行动”；Superpower 则用 HARD-GATE、反例、checklist、状态图和关键原则重复，让同一套约束更显眼、更难被跳过。

写这类 skill 时，重点是明确不可跳过的门槛、真实的审批点和步骤状态。复杂流程可借鉴 Superpower 的多层约束；简单场景则可以像 grilling 一样，只保留最关键的几条规则。