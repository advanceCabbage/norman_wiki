# OpenClaw 源码学习大纲：把 Agent Runtime 产品化为多渠道 Gateway

> 本目录的原始笔记显示：OpenClaw 的定位不是再写一个底层 Agent Loop，而是把 Agent 放入可接入多个通信渠道、可路由、可治理、可定时运行的 Gateway 平台。默认运行时是 Pi，也可经 Harness 换成 Codex。

## 一、总心智模型

```text
WhatsApp / Telegram / Slack / Webhook / 设备节点
                     ↓
       Channel Plugin：验签、认证、入站归一化
                     ↓
  Gateway：路由、会话、记忆、工具策略、权限、沙箱、调度
                     ↓
       Agent Runtime Harness：Pi（默认）/ Codex（可替换）
                     ↓
模型、工具执行、事件流、回复结果
                     ↓
Reply Dispatcher / Outbound Adapter：按渠道能力投递
```

一句话：**Pi 解决“一个 Agent 怎样运行”；OpenClaw 解决“谁可以从哪个渠道驱动哪个 Agent，并让它安全、可靠地持续运行”。**

## 二、模块地图

### 2.1 Gateway 与路由：平台的控制平面

对应笔记：[openclaw 通信渠道机制原理](openclaw%20通信渠道机制原理.md)、[openclaw与pi-coding-%20agent的依赖关系](openclaw与pi-coding-%20agent的依赖关系.md)。

- Gateway 接收渠道消息，确定 `channel + accountId + peer`，路由到 Agent 与 session。
- OpenClaw 将 Pi 当作嵌入式 SDK（`AgentSession`、`SessionManager`、工具协议、Skill/Extension、Compaction），而不是拉起 Pi CLI 子进程。
- 平台层负责多渠道接入、会话排队、权限过滤、沙箱、记忆、长输出防护、上下文溢出恢复和最终回复渲染。
- 多用户隔离有三个层次：同 Agent、按 session 隔离（仅隔离对话）；按用户创建 Agent（工作区与记忆隔离）；每用户独立 Gateway/Pod（进程与持久卷隔离）。

### 2.2 Channel Plugin：边缘适配，而非在核心里写平台分支

对应笔记：[openclaw 通信渠道机制原理](openclaw%20通信渠道机制原理.md)。

- **Channel Plugin**：完整渠道实现，负责配置、生命周期、认证、Webhook/Socket/轮询、发送、状态和渠道能力声明。
- **ChannelDock**：轻量共享差异层，向核心暴露身份格式化、默认目标、群聊 `requireMention`、群聊工具策略、线程上下文、target 规范化与能力声明；核心不需要加载各渠道沉重 SDK。
- **Monitor / Outbound Adapter**：前者监听并规范化入站事件，后者适配文本分块、媒体、引用回复和线程等平台能力。
- 通用回复流先进入 `ReplyDispatcher`；支持流式的平台可以分块/编辑，不支持的平台可缓冲后发送最终内容。

**开发一个新渠道的最小闭环**：验签与幂等去重 → 稳定身份/群 ID 归一化 → `MsgContext` 与 session 路由 → DM pairing/allowlist/mention 门控 → 出站分块与失败重试 → 针对串会话、越权、媒体和重复事件测试。

### 2.3 多层权限与工具治理：入口授权不等于执行授权

对应笔记：[openclaw权限控制机制](openclaw权限控制机制.md)、[openclaw工具加载机制](openclaw工具加载机制.md)。

- **Gateway 控制面**：`operator.admin` 管理配置、Agent、Skill 与受控文件；已配对 `node` 只处理节点专属 RPC。
- **聊天入口**：`guest` 不能驱动 Agent；`user` 仅使用基础工具；渠道 owner / `chat-admin` 可使用 owner-only 管理工具。
- **工具暴露**：先汇总核心编码工具、OpenClaw 工具、渠道工具和插件工具，再依次经过 profile、全局、Provider、Agent、群聊、沙箱、子 Agent、owner-only 等策略过滤；模型只看到最后允许的 JSON Schema。
- **执行钩子**：`before_tool_call` 可拦截/改写参数，`after_tool_call` 用于审计；`tool_result_persist` 与 `before_message_write` 可在落会话前脱敏、缩短或阻止敏感结果持久化。
- **子 Agent 限制**：默认不得触及 gateway、cron、memory、直接跨 session 发送等系统能力；可选插件工具默认不加载，需显式 allowlist。

**关键边界**：渠道身份回答“谁能发起任务”，工具策略、审批与沙箱回答“这个任务实际能做什么”。

### 2.4 记忆与上下文：面向长期服务的四层设计

对应笔记：[openclaw 记忆机制](openclaw%20记忆机制.md)。

| 层 | 内容 | 主要载体 | 如何服务模型 |
| --- | --- | --- | --- |
| 身份/行为上下文 | 规则、用户画像、工具备注 | `AGENTS.md`、`SOUL.md`、`USER.md` 等 | 启动时 bootstrap 注入 |
| 长期记忆 | 决策、偏好、稳定事实 | `MEMORY.md`、`memory/**/*.md` | 向量 + FTS 混合检索 |
| 会话历史 | 原始消息、工具、摘要 | `sessions/*.jsonl` | 恢复同一 session |
| 检索索引 | 分块、embedding、FTS 元数据 | agent 对应 SQLite | 只供检索工具使用 |

- 长期记忆使用 SQLite 中的向量与全文混合检索；笔记记录默认最多返回 6 条，向量/FTS 权重约为 0.7/0.3。
- `MEMORY.md` 较短时可直接进入 bootstrap，过长时只取头尾；模型依据系统提示在旧决策、人物、偏好、待办、日期等场景自行决定是否检索。
- 压缩前有 memory flush，将重要事实写入 Markdown，避免它仅存在于会话摘要。
- 默认 compaction 复用 Pi Agent SDK；OpenClaw 还可在 Provider 支持 cache TTL 时裁剪旧工具输出。

**风险提示**：同 Agent 的不同 session 仍共享工作区与记忆索引，容易发生个性化记忆串人；真正多租户必须提升到独立 Agent 或独立实例。

### 2.5 工具输出与上下文溢出：四道防线

对应笔记：[openclaw工具加载机制](openclaw工具加载机制.md)。

1. 工具本身分页、`offset/limit`，避免一次读入超大对象。
2. 写入会话前有硬上限（笔记中为约 400,000 字符）。
3. 下一轮模型上下文再按单条、总预算与新旧程度裁剪。
4. 模型仍溢出时，对历史超大结果做恢复性截断并重试。

企业可通过持久化 Hook 做脱敏、网页摘要替换或敏感输出禁存。这里的取舍是：平台可靠性优先于“永久保留工具返回的每个字”。

### 2.6 Cron 与 Heartbeat：从对话式 Agent 到持续运行的系统

对应笔记：[openclaw定时任务机制](openclaw定时任务机制.md)。

- CronService 只维护一个围绕最早到期任务的全局 timer，最长每 60 秒重新检查，避免每个任务各自持有长期定时器。
- 支持 `at`、`every`、`cron`（含 IANA 时区）三种排期。
- `main` 将事件送回已有主会话/Heartbeat；`isolated` 创建独立 Cron Session 并运行完整 Agent Loop。自然语言任务默认偏向 isolated，只有明确需要复用主会话时才选 main。
- 先持久化 `runningAtMs` 再执行，防重复并发；循环任务按错误次数退避（30 秒到 1 小时），排期计算连续 3 次失败后禁用；单次 Job 还有 watchdog。

**面试重点**：定时任务不是“到点调模型”这么简单，还必须回答幂等、并发、持久化、重启恢复、失败退避、超时和时区。

### 2.7 Runtime 可插拔：平台层和执行层分离

对应笔记：[openclaw可插拔机制](openclaw可插拔机制.md)。

- 默认由 Pi 提供 Agent Loop、Session、工具协议、Skill/Extension 与 compaction。
- 启用 Codex Harness 并设置 `agentRuntime.id: "codex"` 后，内层 Agent Loop 与原生工作区工具转由 Codex App Server 执行；OpenClaw 仍负责渠道、会话镜像、模型路由、审批、媒体、动态工具与外围记忆治理。
- 这不是“把 OpenClaw 换成 Codex”，而是**外层平台控制与内层执行 Runtime 的双层协作**。
- 真正难点包括 Harness 能力协商、双会话绑定、取消/失败闭环，及不同 Runtime 工具语义不被静默降级。

## 三、推荐学习顺序

1. 先读 OpenClaw 与 Pi 的依赖关系，明确边界。
2. 再读渠道插件与路由，理解平台为何能接入多入口。
3. 接着读权限、工具策略、沙箱和输出防护，理解企业化治理。
4. 最后读记忆、Cron、可插拔 Runtime，理解长期运行与多租户问题。

## 四、30 秒面试总结

OpenClaw 是一个 Agent Gateway 平台，不是单独的模型循环。它在边缘用 Channel Plugin 将不同平台消息归一化，在中心按身份、账户和会话路由到 Agent，并通过工具策略、审批、沙箱和持久化 Hook 做治理；默认复用 Pi 作为嵌入式 Runtime，同时可以用 Harness 替换为 Codex。它的优势是多渠道、多租户、长期记忆和定时运行的产品化能力；代价是会话/记忆隔离、渠道身份规范化、跨 Runtime 语义一致性都必须被严格设计与运维。
