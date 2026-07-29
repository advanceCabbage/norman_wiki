# Claude Code、OpenClaw、Pi：横向对比与面试框架

> 对比依据为同级目录下的源码分析笔记。最重要的前提是：**三者并非严格同层竞品。** Pi 是 Agent Runtime/组件栈；OpenClaw 是可接入 Pi 或 Codex 的 Gateway 平台；Claude Code 是完整的软件工程 Agent 产品与运行时。面试先对齐层级，才能谈优劣。

## 一、先给结论：三者的关系

```text
                ┌─────────────────────────────────┐
                │             OpenClaw             │
                │ 多渠道、路由、权限、记忆、Cron、沙箱 │
                └──────────────┬──────────────────┘
                               │ Harness
                    ┌──────────┴──────────┐
                    ↓                     ↓
        Pi Runtime（默认）          Codex Runtime（可选）
        模型适配、Loop、Session、Tool      原生线程与工作区工具

Claude Code：一条独立的、面向软件工程的产品/运行时纵向栈
Prompt + Tool Runtime + Permission + Session + Context + Multi-Agent
```

- **Pi**：提供“造 Agent”所需的通用积木与编码 Agent 参考产品。
- **OpenClaw**：提供“把 Agent 放进真实沟通和运营环境”所需的平台层能力。
- **Claude Code**：提供“让 Agent 在代码库中可靠完成工程任务”所需的垂直整合能力。

因此，“OpenClaw 比 Pi 多渠道”并非 Pi 的缺陷；“Pi 比 OpenClaw 更贴近 Loop”也不是 OpenClaw 的缺陷。它们本来解决不同层的问题。

## 二、一张总表：从 10 个维度对齐

| 维度 | Claude Code | OpenClaw | Pi Agent |
| --- | --- | --- | --- |
| 核心定位 | 软件工程 Agent 产品与 Runtime | 多渠道、长期运行的 Agent Gateway | 可嵌入、可组合的 Agent 组件栈 |
| 主要用户 | 在代码库中开发、修改、审查、验证的工程师 | 需要把 Agent 接到聊天渠道、设备、定时任务的产品/平台团队 | 想构建 CLI、IDE、SDK、定制 Agent 的开发者 |
| Agent Loop | 纵向整合的 Query Loop，支持 Tool、权限、多 Agent | 默认委托 Pi；可经 Harness 换成 Codex | `pi-agent-core` 提供通用 Loop，coding-agent 提供产品层外循环 |
| 模型接入 | 产品内的模型与认证能力，Prompt/工具组织高度工程化 | 由平台模型路由 + 选定 Runtime 共同承担 | `pi-ai` 将多 Provider/流式/Tool Call 统一化 |
| 会话模型 | JSONL transcript + UUID 链 + 文件历史/模式等状态 | 渠道路由会话与 session 镜像；内层 Runtime 管理其会话 | JSONL 追加式会话树，`id + parentId + leaf` |
| 长期记忆 | 核心记忆 + selector 按需注入，重视 compact 后恢复 | Markdown 长期记忆 + SQLite 向量/FTS；面向多会话/多用户 | 重点是 Session/资源/压缩，长期记忆由宿主产品定义 |
| 工具治理 | Schema、Permission、Sandbox、Hook、并发安全和审批 UI | 候选工具经渠道/群聊/owner/沙箱/子 Agent 策略过滤 | 工具注册与 active 集分离、Hook 与执行环境可插拔 |
| 扩展模型 | Skill、Hook、MCP、Subagent、动态工具发现 | Channel Plugin、Tool Plugin、Runtime Harness、持久化 Hook | ExtensionAPI、Hook、Skill、Provider、TUI 组件 |
| 多 Agent | Subagent、Fork、Coordinator，强调上下文隔离与缓存 | 平台可限制子 Agent 系统能力；实际内层取决于 Runtime | 提供底层事件/队列/Harness 能力，产品层可自行编排 |
| 长期运行能力 | 聚焦会话内的软件工程任务 | Channel、Cron、Heartbeat、重试、超时、隔离会话是核心能力 | 可嵌入 RPC/Server，但不主打渠道运营 |

## 三、核心维度的深入比较

### 3.1 架构取舍：垂直整合 vs 平台编排 vs 分层组件

| 框架 | 优势 | 代价 / 风险 | 适合场景 |
| --- | --- | --- | --- |
| Claude Code | 工具、权限、上下文、会话、验证与协作形成一致体验；工程任务路径短 | Runtime 机制与产品约束较强，深度定制需遵循其生态 | 复杂代码库改造、调试、评审、日常研发 |
| OpenClaw | 把渠道、身份、路由、记忆、Cron 和运行时解耦；可换内层 Runtime | 双层状态与跨 Runtime 语义更复杂；多租户隔离不能只靠 session | 多渠道 AI 助手、企业 Gateway、长期自动化、Agent 运营平台 |
| Pi | 核心包边界清晰，Loop/模型/工具/存储/UI 可替换、可嵌入 | 产品级权限、渠道、多租户、运营能力需由宿主补齐 | 自研 Agent 产品、IDE/CLI 集成、需要控制 Runtime 的团队 |

### 3.2 Context 与 Memory：都在“长期”，但治理对象不同

| 问题 | Claude Code | OpenClaw | Pi |
| --- | --- | --- | --- |
| 持久化原始历史 | 追加式 transcript；按 UUID/边界恢复有效链 | session JSONL，平台可在外层管理路由与镜像 | JSONL 会话树；当前上下文是 leaf 路径投影 |
| 压缩目标 | 避免模型上下文爆炸，同时重建必要运行状态 | 默认委托 Pi 压缩；另有 memory flush 与工具输出治理 | 结构化摘要 + 最近约 20K token 尾部；防无限重试 |
| 长期知识 | 独立 selector 选少量相关记忆再注入 | `MEMORY.md`/daily memory + 向量/FTS 混合检索 | 不把业务长期记忆作为核心职责，交由宿主 |
| 最大风险 | 把不可丢失运行时约束交给摘要 | 同 Agent 多用户共享 workspace/记忆导致串人 | 将 session 历史误当成完整产品记忆系统 |

**面试的高质量回答**：Claude Code 重点解决“一个复杂工程会话如何可恢复地继续”；OpenClaw 额外解决“多个渠道、用户和长期事实如何被治理”；Pi 提供会话与压缩积木，但是否建设长期记忆库是宿主决策。

### 3.3 Tool 与安全：三层都存在，但责任边界不同

```text
入口可信？             OpenClaw：DM pairing / allowlist / mention / 渠道验签
任务能请求什么？        Claude Code / Pi：模型可见的 Tool Schema 与 active tools
请求是否真正执行？      Claude Code：Permission / Sandbox / approval；
                        Pi：Tool 后端与 Hook；OpenClaw：平台策略再过滤
结果能否保存/外发？     OpenClaw：persist Hook、脱敏、渠道投递策略
```

- Claude Code 的亮点是将审批、受保护路径、allow/deny 与文件修改/回退深度整合，适合高频工程写操作。
- OpenClaw 的亮点是将“谁可以驱动 Agent”与“该人能看见哪些工具”放在多渠道、多角色、子 Agent 的平台策略中。
- Pi 的亮点是将工具注册、激活集合、执行环境和 Hook 抽象为宿主可替换能力；它提供机制，不替代企业安全设计。

### 3.4 扩展性：不要把 Hook 当作 Sandbox

| 框架 | 主要扩展点 | 价值 | 必须说明的限制 |
| --- | --- | --- | --- |
| Claude Code | Skill、MCP、Hook、Subagent、Tool Search | 渐进能力加载与工程工作流沉淀 | Prompt/Skill 不是强制安全边界 |
| OpenClaw | Channel Plugin、Tool Plugin、Runtime Harness、持久化 Hook | 新渠道和新 Runtime 不必侵入核心 Gateway | 渠道插件必须做好验签、稳定身份和串会话测试 |
| Pi | ExtensionAPI、Hook、Provider、Skill、TUI | 可在不改 Loop 的情况下组合产品能力 | 扩展代码运行在进程内，wrapper 不是沙箱 |

### 3.5 并发与多 Agent：不要只问“支不支持”

- **Claude Code**：最完整地将多 Agent 作为产品能力处理。它按字段复制/隔离状态、收紧工具、用消息回注入通信，并以 Fork 缓存复用降低并发成本；Coordinator 面向大型并行工程任务。
- **OpenClaw**：更关注并发任务在多渠道、多 session 与 Cron 下的可靠运行；子 Agent 被限制系统级能力，防止聊天入口间接获得平台管理权限。
- **Pi**：提供单 run 并发守卫、工具批次并发、steering/follow-up 队列和 Harness 基础；上层如何组织多人协作由 coding-agent 或宿主产品决定。

## 四、三个高频面试问题与示范回答

### Q1：Claude Code、OpenClaw、Pi 谁更强？

不能脱离层级回答。Claude Code 在“代码库内完成工程任务”这一垂直场景中整合最深；OpenClaw 在“多渠道、多用户、定时和长期运营”上更完整；Pi 在“自定义、嵌入和重组 Agent Runtime”上最轻量、最灵活。实际选择通常是 Claude Code 直接服务研发，或 OpenClaw 在外层接入 Pi/Codex；Pi 则用于自建 Agent 产品底座。

### Q2：为什么 OpenClaw 已有 Pi，还要支持 Codex Harness？

因为 Gateway 的平台职责和 Agent 执行职责可以独立演进。Pi 擅长通用嵌入式 Runtime；Codex 有自己的线程、工作区工具和代码 Agent 生态。通过 Harness 替换内层执行器，OpenClaw 无需复制渠道、路由、权限、媒体、调度等平台能力。代价是必须处理能力协商、会话绑定、取消和工具语义差异，不能把“可切换”误解成零成本替换。

### Q3：三者如何处理长上下文？

Pi 的基础策略是结构化 compaction 加最近原始尾部，并限制 overflow 重试次数；Claude Code 在此之上形成多层治理，包括大工具结果外置、snip、microcompact、auto/reactive compact，并在压缩后重建 Skill、Plan、Agent 等运行状态；OpenClaw 默认可复用 Pi 的压缩，同时在平台外层管理长期 Markdown 记忆、向量/FTS 检索、memory flush 和渠道会话隔离。三者都不应把“直接截掉旧聊天”当作完整方案。

## 五、面试表达模板：先定位，再比较，再给选择

```text
第一句：先说层级。
“Pi 是 Runtime，OpenClaw 是平台层，Claude Code 是工程 Agent 产品，不能直接把功能数相减。”

第二句：说各自不可替代的价值。
“Pi 的价值是可嵌入和可组合；OpenClaw 的价值是渠道、租户、调度与治理；Claude Code 的价值是面向代码任务的安全工具闭环和上下文治理。”

第三句：说代价和选型。
“需要现成研发体验选 Claude Code；需要多渠道长期服务选 OpenClaw，并选择 Pi 或 Codex 作内核；需要自己定义 Runtime 语义和产品形态选 Pi。”
```

## 六、建议的复习路径

1. 先背本页第一节的层级关系，避免任何比较题答偏。
2. 分别读三个目录的《源码学习大纲》，对每个模块能回答“职责、关键机制、收益、代价”。
3. 用第二节的 10 维表格做抽问练习。
4. 用第四节三道题做 60 秒口述；重点练“不是同层竞品”和“边界/代价”两句话。
