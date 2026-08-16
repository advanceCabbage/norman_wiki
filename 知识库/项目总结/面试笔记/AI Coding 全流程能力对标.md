# AI Coding 全流程能力对标（面试用）

> 针对 JD：「展示如何利用 AI Coding 助手完成从需求分析到代码落地的全流程，能通过 Prompt 引导 AI 生成高质量代码，了解如何通过 AI 工具快速原型验证（POC）和迭代」
> 调研时间：2026-08-10

## 一、先给结论

我现有的弹药（7 个编程提示词、Boris 的 5 条习惯、Plan 模式、`/grilling`）**方向全对，而且每一条都能在官方 best practices 里找到对应**，问题不在"用得浅"，在两点：

1. **覆盖面偏科**。这些全部落在「实现」这一段。JD 要的是「需求分析 → 落地」的**全流程**，我在**需求侧（产出物）**和**交付侧（验证/评审/度量）**基本是空的，POC 那一段更是一个字没提。
2. **叙事层级偏低**。业界 2026 年的分水岭已经不是"会不会写提示词"，而是**Context Engineering / Harness Engineering**——即把每次失败沉淀成配置与门禁。Addy Osmani 那句话是这一年的共识：「一个普通模型配好 harness，胜过一个强模型配烂 harness」。我笔记里其实已经有整套 Harness 三层（见 `收藏箱/【精】一文读懂Harness Engineering.md`），但没有进面试故事，等于白有。

一句话：**不是要换方案，是要把「提示词技巧」升维成「工程系统」，并把两头补齐。**

## 二、业界成熟度分层（用来定位自己）

| 层级 | 代表实践 | 我的现状 |
|---|---|---|
| L1 提示词技巧 | 分场景提示词、先读后改、对抗性测试 | ✅ 已有（7 个提示词） |
| L2 项目配置 / 上下文工程 | CLAUDE.md 活文件、Skill、Hook、权限白名单、subagent 隔离调研、`/clear` 与 compact 策略 | ⚠️ 部分（知道 Boris 那 5 条，但没有自己的沉淀证据） |
| L3 规格驱动 + 可验证闭环 | SPEC.md / Spec Kit / Kiro，EARS 验收标准；机器可判定的 done（测试、Stop hook、`/goal`）；生成者与评审者分离 | ❌ 只有 Plan 模式，没有产物、没有硬门禁 |
| L4 并行编排 + 评审基础设施 + 度量 | worktree 多会话、Writer/Reviewer 双会话、`claude -p` 批量 fan-out、agent team；自动化一审 + 风险分级；DORA 口径度量 | ❌ 缺 |

面试官问"全流程"，考的其实是 L3/L4；答 L1 就会被判定为"浅"。

## 三、五个缺口 + 怎么补

### 缺口 1：需求侧没有**产物**，只有对话

Plan 模式和 `/grilling` 是好动作，但它们的结果留在会话里，会话一关就没了。

业界做法（由轻到重）：

- **官方最轻的做法**（Claude Code 文档明写）：先让 AI 反过来面试我，把结论写成 `SPEC.md`，然后**开新会话**执行——新会话上下文干净，只干实现。
  > 提示词模板：`I want to build [X]. Interview me in detail using the AskUserQuestion tool. Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs. Don't ask obvious questions, dig into the hard parts I might not have considered. Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.`
  > 好的 spec 特征：点名涉及的文件与接口、写清**不做什么**、结尾必须有一条端到端验证步骤。
- **规格驱动开发（SDD）**：2026 年主流化。规格（而非代码）是版本化的唯一事实源。
  - GitHub **Spec Kit**：`specify → plan → tasks → implement` 四阶段 + 一份全局 **constitution**（不可变原则，每个 spec 都继承）。
  - AWS **Kiro**：需求 → 设计 → 任务三份文档，验收标准用 **EARS** 句式写。
  - **OpenSpec**：极轻量，纯 Markdown。**BMAD**：最重，模拟 12+ 角色的敏捷团队。
  - 关键判断（这句在面试里比罗列工具值钱）：**SDD 有成本，小改动用它是负收益**；它的价值在多人协作、跨会话、返工代价高的需求上。

**我的升级**：`/grilling` 拷问完 → 落一份 `SPEC.md`（含范围、非目标、验收标准、验证方式）→ 新会话实现。这样"需求分析"就有了可展示的实物。

### 缺口 2：没有**机器可判定的 done**

官方 best practices 把这条排在**第一位**：「Give Claude a way to verify its work」。核心逻辑是——没有 AI 自己能跑的检查，"看起来做完了"就是唯一信号，**人就变成了验证循环本身**。

四级递进（面试可以直接背这个梯度）：

1. **提示词内自查**：把验收用例写进 prompt，让它实现后自己跑。
2. **`/goal` 条件**：独立评估器每轮结束后复检，不满足就继续干。
3. **Stop hook 硬门禁**：检查脚本不通过就不允许结束这一轮（连续 8 次会被强制放行）。
4. **独立评审 subagent**：新上下文只看 diff 和验收标准，不看生成过程——**运动员不能当裁判员**。

配套原则：**要证据不要结论**——让它贴出测试输出、执行的命令与返回、截图，而不是说"已完成"。
反向提醒（这条能体现分寸感）：评审 agent 被要求找问题就一定找得出问题，要限定"只报影响正确性和既定需求的缺口"，否则会诱发过度设计。

我的第 5、6 条提示词（对抗性测试、Code Review 忽略风格）正好是第 4 级的手工版——**把它升级成 subagent + hook，就从"技巧"变成"机制"**。

### 缺口 3：Context Engineering 没进故事

2026 年的共识：**上下文工程已取代提示词工程成为核心学科**。所有前沿模型在上下文填满**之前**就开始变差，解法不是更大的窗口，而是**预算纪律**。

可讲的点（我 Harness 笔记里全有，只是没往面试上接）：

- CLAUDE.md 的判据：**"删掉这行会不会让它犯错？"** 不会就删。太长 = 规则被淹没 = 它开始无视你。
- OpenAI 的 AGENT.md 只有约 100 行，**是目录不是百科**；再配一个 Doc-gardening Agent 每天巡逻，**过期的记忆比没有记忆更危险**。
- 调研类任务丢给 subagent（独立上下文，只回摘要），主会话留给实现。
- 无关任务之间 `/clear`；同一个问题纠正超过两次就是上下文已污染，清掉重写 prompt 比继续纠正更快。
- 代码检索优先用**代码智能（LSP/符号跳转）**而非纯文本 top-k——拿到的是真定义，不是"可能包含这个字符串的文件"。

### 缺口 4：并行与编排

- **git worktree 多会话**：每个 agent 一个独立工作目录、共享一个 `.git`，避免文件写冲突与 checkout 互踩（JetBrains 2026.1、VS Code 都已原生支持 worktree）。
- **Writer / Reviewer 双会话**：新上下文做评审，不会偏袒自己刚写的代码。同理可做"一个写测试、一个写实现"。
- **fan-out 批量**：大迁移用 `claude -p` 循环 + `--allowedTools` 限权，先跑 2-3 个文件调 prompt，再全量。
- 反面教训（比正面经验更有说服力）：多 agent 并发时最典型的翻车是**集成期同一个 bug 被多个 agent 同时修，互相覆盖**；解法是控制流门禁（Planner/Worker/Judge + DAG 单向调度）与只读沙箱（评审者无权改测试脚本）。

### 缺口 5：POC 这一段完全没答（JD 明确写了）

业界做法：

- **一次性原型（throwaway prototype）**：让 agent 在一条临时路由下并排生成 **3 个可点击的方案**，肉眼比完再定稿——**在写真代码之前**先收敛 UI/交互，比用文字向 agent 描述 UI 高效得多。
- **截图即验收标准**：给设计稿 → 实现 → 自己截图对比 → 列差异 → 修。这是"视觉任务"的可验证闭环。
- **纪律**：超过一半的 AI 原型进不了生产，卡在架构、安全、测试、可维护性。**所以原型的正确归宿是"读完就扔、按 spec 重写"，不是直接提交**。能主动说出这条，比说"我用 AI 三天做了个 demo"分量重得多。

## 四、度量与风险（拉开层次的部分）

- **DORA 2025**：AI 采用率约 90%；AI **提升吞吐但同时放大不稳定性**——"没有稳定性的速度只是加速的混乱"。核心结论是 **AI 是放大器**：强团队更强，烂流程更烂。
- DORA 给出**放大 AI 收益的七项能力**：清晰的 AI 立场、健康的数据生态、内部数据对 AI 可达、**强版本控制实践**、**小批量作业**、用户导向、高质量内部平台。（注意：**缺乏用户导向的团队，采用 AI 反而是负收益**。）
- **瓶颈已经从"写"转移到"评审"**：LinearB 2026 基准显示 AI 生成的 PR 拿起时间约为普通 PR 的 5.3 倍、评审时长大幅上升，AI PR 接受率约 32.7%（人工约 84.4%）。
- 由此推出的正确姿势：**小批量提交 + 自动化一审（格式/安全/已知漏洞交给机器）+ 人只看意图与架构契合 + PR 里附行为证据**。

## 五、面试可直接讲的一条主线

> "我把 AI 编码当成一条有门禁的流水线，而不是一个会写代码的聊天框。"

1. **需求分析**：先用拷问式提问（我有一个 `/grilling` skill）把模糊需求打穿，产出 `SPEC.md`——范围、非目标、验收标准、端到端验证方式，然后**开新会话**执行，避免把讨论垃圾带进实现上下文。
2. **方案**：复杂需求一律 Plan 模式，先只读探查再出方案，方案我会亲自改，确认后才允许动代码。小改动**不走这套**——规格驱动是有成本的。
3. **实现**：CLAUDE.md 是活文件（每一条规则都能追溯到一次踩坑），高频动作做成 skill，格式化/lint 这类必然发生的动作用 hook 而不是靠提示词自觉。
4. **验证**：核心原则是"给它一个自己能跑的检查"。轻的写进 prompt，重的挂 Stop hook；最后一定有一个**独立上下文的评审 subagent** 只看 diff 和验收标准——生成者不能当裁判员。要它给证据（测试输出、截图），不要它给结论。
5. **POC / 迭代**：先在一次性路由里并排出 2-3 版可点的原型收敛方向，截图做验收基准；原型确认后**按 spec 重写**进生产，因为原型的架构/安全/测试基本都是欠账。
6. **规模化与风险**：多任务用 worktree 并行、批量迁移用 headless fan-out；同时我清楚 DORA 2025 的结论——AI 提吞吐也放大不稳定，所以我坚持小批量提交和自动化一审，因为**瓶颈已经从写代码转移到评审**。

配套弹药（用我自己的项目落地）：`基于 openClaw 的 MSI 端到端智能测试工作流`、`文档代码一致性智能检测工具`、`智能客服 RAG` ——分别对应"把流程做成 agent 工作流""把验证做成工具""把检索做对"。

## 六、面试前值得补的最小动作

按性价比排序（每条都能变成可展示的实物）：

1. **写一个 `/spec` skill**：拷问 → 生成 `SPEC.md`（含非目标与验收标准）→ 提示开新会话执行。**半天，收益最大**，直接补上"需求分析"这一环。
2. **在本仓库挂一个 Stop hook / 验证脚本**：哪怕只是 lint + 测试，能讲"我把 done 的判定从人挪到了机器"。
3. **精简一份 CLAUDE.md，并给每条规则标注来源踩坑**——现场展示"每一行都可追溯"，这是 harness 心态的最好证据。
4. **跑一次 worktree 并行 + Writer/Reviewer 双会话**，留下截图或记录。
5. **准备两三个数字**：某次需求的返工次数、评审耗时、bug 逃逸——哪怕是粗口径，有度量意识就赢过 90% 的候选人。
6. **准备一条"什么时候不该用 AI/不该走重流程"**：小改动不写 spec、评审 agent 报的问题不全修（会导致过度设计）、原型不直接进生产。**分寸感是资深与否的分水岭。**

## 参考来源

- [Best practices for Claude Code（官方）](https://code.claude.com/docs/en/best-practices)
- [Agent Harness Engineering — Addy Osmani](https://addyosmani.com/blog/agent-harness-engineering/)
- [DORA | State of AI-assisted Software Development 2025](https://dora.dev/dora-report-2025/)
- [2025 DORA AI Capabilities Model (PDF)](https://services.google.com/fh/files/misc/2025_dora_ai_capabilities_model.pdf)
- [Spec-Driven Development in 2026（工具与实践综述）](https://dev.to/krlz/spec-driven-development-in-2026-what-it-is-the-tooling-and-how-teams-actually-use-it-2fk2)
- [BMAD vs Spec Kit vs OpenSpec 对比](https://medium.com/@reenbit/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework-in-2026-a6996b3ebb8d)
- [Context Engineering: A Practical Guide for AI Agents (2026) — Sourcegraph](https://sourcegraph.com/blog/context-engineering)
- [AI Code Review Is the New Bottleneck in Agentic Coding — Moderne](https://moderne.ai/blog/ai-didnt-break-coding-it-broke-code-review)
- [The Human Review Bottleneck: Review Strategies for Agent Output](https://codex.danielvaughan.com/2026/05/24/human-review-bottleneck-code-review-strategies-agent-output/)
- [Throwaway UI Prototypes: Stop Describing UI to Agents](https://blog.alexrusin.com/throwaway-ui-prototypes-ai-agents/)
- [Professional Software Developers Don't Vibe, They Control (arXiv)](https://arxiv.org/pdf/2512.14012)
- [Git worktrees for parallel AI coding agents](https://developer.upsun.com/posts/ai/git-worktrees-for-parallel-ai-agent-execution)

## 相关笔记

- `收藏箱/【精】一文读懂Harness Engineering.md`（Harness 三层，本文 L2-L4 的理论底座）
- `收藏箱/【精】Loop Engineering又是啥？一文讲清企业Agent落地的四层工程进化论.md`
- `知识沉淀/源码系列/Claude code源码/Boris 自己平时怎么用 Claude Code？.md`
- `知识沉淀/7 个 AI 编程提示词.md`
- `知识沉淀/如何写好skill.md`
