# Pi Agent 源码学习大纲：可嵌入、可组合的 Agent 组件栈

> Pi 的价值在于把 Agent 系统拆成可复用 npm 包：模型协议、Agent Loop、编码产品层、TUI 和可选存储分别独立。它不是只为 CLI 而写的单体，而是一套可被宿主嵌入与替换的组件栈。

## 一、总心智模型与依赖方向

```text
pi-server（实验性多实例管理）
        ↓
pi-coding-agent（CLI / SDK 产品层） ───→ pi-tui
        ↓                 ↘
pi-agent-core（通用 Loop / Tool / Harness）
        ↓
pi-ai（多 Provider 协议适配）

pi-storage-sqlite-node：可选 Session 存储实现
```

依赖必须自下而上理解：`pi-ai` 统一“如何和模型说话”；`pi-agent-core` 统一“如何循环与调用工具”；`pi-coding-agent` 统一“如何成为一个编码产品”。

## 二、模块地图

### 2.1 pi-ai：多 Provider LLM 协议层

对应笔记：[Pi-ai详解](Pi-ai详解.md)、[Pi 分层架构设计](Pi%20分层架构设计.md)。

- 统一请求、消息、停止原因、工具定义、工具结果、流式 Tool Call 参数、Token/缓存用量与错误。
- 对不同厂商的流式协议统一输出文本、思考、工具调用、完成、错误等事件。
- 对不支持视觉的模型将图片降级为文本占位，避免上层业务为每个 Provider 分叉。
- 笔记记录其支持多 Provider，并复用多类文本协议适配器；适配器职责是“Pi 统一对象 → 厂商请求”“厂商流 → Pi 统一事件”。

**边界**：它是 LLM Gateway/adapter，不负责 Agent 循环、工具执行权限或产品会话。

### 2.2 pi-agent-core：Agent Loop 与通用运行时内核

对应笔记：[Pi-agent-core详解](Pi-agent-core详解.md)。

#### Loop 与事件

- 执行核心是 `runAgentLoop()`：构建上下文 → 调模型流 → 组装 assistant message → 执行工具 → 写入 tool result → 再次推理。
- 流式 UI 不必理解 Provider 协议，只需订阅 `message_update` 等统一事件。
- 工具参数若因模型 `length` 截断，工具不执行；找不到工具、参数错误、Hook 拦截、工具异常都会转换为 `ToolResultMessage(isError: true)` 回给模型，避免整个 Agent 直接崩溃。
- `terminate` 为批次级语义：只有同一批工具结果都要求终止，Loop 才结束，避免单工具中断吞掉同批其他结果。

#### 状态与消息注入

- 状态分为配置状态（模型、工具、System Prompt、思考级别）、对话状态（完成消息）和运行状态（流式消息、待执行工具、错误）。
- `streamingMessage` 与已完成 `messages` 分离，避免把半截 Tool Call 或半截回答作为下一轮历史。
- 通过 steering、follow-up、next-turn 区分“本轮工具批次结束前插入”“本次 run 收尾后继续”“下次外部 `prompt()` 前排队”的时序。
- `AgentHarness` 是 Agent Loop 之上的高阶产品化运行时；笔记特别指出 `pi-coding-agent` 使用的是 `Agent` 编排，不应把二者混为一谈。

#### 工具与 Hook

- 工具定义、执行环境、上下文注入和执行后端可插拔；工具注册集与本轮 active tools 集分离。
- active tools 使最小权限、阶段化工作流和上下文成本控制成为可能，但修改 tools 数组会破坏 Anthropic 前缀缓存中的工具段。
- 默认工具批次可并发；需要串行的工具或全局配置会形成批次屏障。工具结果虽然按完成顺序产生事件，回灌模型时仍按原 assistant 中的调用顺序保持稳定。

### 2.3 pi-coding-agent：面向编码的产品编排层

对应笔记：[Pi-Coding-agent 详解](Pi-Coding-agent%20详解.md)。

#### 四种交互模式

- `interactive`：TUI 交互。
- `print`：一次性输出。
- `json`：一轮结构化事件流。
- `rpc`：通过 stdin/stdout JSONL 供任意语言宿主或 IDE 集成。

Interactive 模式中 `pi-tui` 与 coding-agent 同进程、直接方法调用；RPC 模式才有外部宿主与 `pi --mode rpc` 子进程之间的两次序列化边界。二者复用 `session.prompt()` 之后的 Agent 逻辑。

#### AgentSession：产品层的关键状态机

- `prompt()` 会依次处理扩展命令、输入 Hook、Skill 展开、并发守卫、模型/认证校验、压缩检查与 `before_agent_start`。
- 同一时刻只允许一个 agent run；额外输入必须明确选择排队语义。这是 RPC 事件无需 run ID 也能保持有序的前提。
- 外层 Loop 负责跨 run 的压缩、重试与扩展排队消息；内层 Loop 则由 `pi-agent-core` 负责模型—工具闭环。`agent_end` 与真正的 `agent_settled` 应严格区分。

#### 文件工具、并发与输出保护

- 工具批次默认并发，但同一物理文件的编辑/写入按绝对路径与 `realpath` 建锁串行；注册过程也串行以避免异步解析路径时的竞态。
- `read/grep/find/ls` 偏向保留开头，Bash 偏向保留结尾，grep 单行另做横向截断。这是按工具语义设计，而不是一个全局截断开关。

#### Session 树与会话导航

- 默认一会话一 JSONL，采用追加式 Entry；当前模型上下文从 leaf 沿 `parentId` 回溯得到当前分支路径。
- 同一文件内的历史导航和从历史节点继续会形成树分支；Fork/Clone 才会创建新 JSONL 文件。
- `compaction` 为 Token 治理；`branch_summary` 为离开分支后的任务连续性。两者都不会删除原始 Entry。

#### 七层压缩防御

- 手动、接近 token 预算、模型返回 overflow 都可触发；每个 run 的“压缩+重试”最多一次。
- 通过中断判断、模型切换、最近 compact 边界、完成状态、usage 缺失与“压缩后尚无成功回复”等条件防止误压缩和无限循环。
- 压缩使用“结构化摘要 + 最近约 20K token 的原始尾部”；旧 usage 必须在 compact 后重新判断，不能直接沿用。

### 2.4 扩展、Skill 与 TUI：不修改内核地扩展产品能力

对应笔记：[Pi-Coding-agent 详解](Pi-Coding-agent%20详解.md)、[Pi-agent-core详解](Pi-agent-core详解.md)。

- Extension 通过类型化 `ExtensionAPI` 注册工具、Slash Command、Provider、模型、UI 组件、快捷键、消息渲染器与 Hook；它在 Pi 进程内运行，wrapper 不是安全沙箱。
- Hook 覆盖会话、Agent、消息、工具、Provider、Context、输入/资源和信任边界，可观察也可干预：如阻止工具、改写结果、改请求头、替换压缩、取消导航。
- Skill 对模型先暴露名称、描述与路径，完整正文仅在调用或显式读取时进入上下文。`pi-agent-core` 只负责加载与注入，不对多来源重名 Skill 制定业务优先级；优先级由宿主决定。
- `pi-tui` 是独立终端 UI 库，负责渲染、输入、主题、补全与图片等，不应被误认为 RPC 客户端。

### 2.5 存储与服务层

对应笔记：[Pi 分层架构设计](Pi%20分层架构设计.md)。

- 标准 coding-agent/TUI 以本地 JSONL 作为默认 Session 持久化；`pi-storage-sqlite-node` 是可替换的存储实现。
- `pi-server` 是实验性本地服务层，借 IPC 管理多个 coding-agent RPC 子进程、状态和事件流，本身不直接执行模型调用。

## 三、推荐学习顺序

1. `pi-ai`：先搞清模型协议适配边界。
2. `pi-agent-core`：再理解 Agent Loop、状态、工具与 Hook。
3. `pi-coding-agent`：把通用内核放到编码产品场景，重点读 Session、压缩、工具锁和扩展。
4. RPC/TUI/Server：最后理解同一 Agent 内核如何服务 CLI、IDE 与外部宿主。

## 四、30 秒面试总结

Pi 是一个模块化 Agent 组件栈：`pi-ai` 抹平多模型协议，`pi-agent-core` 提供可嵌入的 Agent Loop、工具与 Hook，`pi-coding-agent` 再把它们编排成具有 Session 树、压缩、扩展、文件工具和 TUI/RPC 模式的编码产品。它的优势是分层清晰、可替换、易嵌入和高度可扩展；代价是宿主需要自行承担渠道、多租户、复杂权限策略等平台能力，且扩展在进程内运行不能被误当作安全沙箱。
