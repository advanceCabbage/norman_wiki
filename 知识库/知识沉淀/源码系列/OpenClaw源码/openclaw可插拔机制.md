#### 一、使用 codex-harness 替换 Pi agent
配置会把 `openai/*` 的 Agent 执行运行时从 Pi 切换为 **Codex app-server**。
可以把三段配置理解为：
- `model: "openai/gpt-5.6-sol"`：选择本轮使用的模型。
- `plugins.entries.codex.enabled: true`：启用 Codex Harness 插件。
- `agentRuntime.id: "codex"`：指定由 Codex 而非 Pi 驱动这次 Agent 运行，并且是“强制模式”——Codex 不可用时直接失败，不回退到 Pi

**代码检索场景**：实际是 Codex 通过原生工作区工具面完成代码查看、搜索和修改

##### 1.1 执行的边界
- OpenClaw 仍负责**渠道消息、会话镜**像、模型路由、审批、媒体，以及执行它自己的动态工具；
- Codex 的原生 Shell / Patch / MCP 调用由 Codex 负责OpenClaw 可观察或拦截部分原生事件，却不会把其参数改写成 OpenClaw 的 `read` / `exec` 调用

#### 二、使用 codex-harness 的一些结论
Codex Runtime 替换的是 Agent 执行器，不替换 OpenClaw 的**工作区记忆和会话系统**；它额外带来一套可选、默认关闭、按 $CODEX_HOME 隔离的 Codex 原生记忆。
- 聊天记录仍在 openclaw 的 session 中
- codex 搜索代码或执行其他任务时，不会引入自己的记忆系统（默认是关闭的）
- 用户显示声明写入记忆文件仍然是写在 MEMORY.md 或 memory/YYYY-MM-DD.md 中
- 使用 Codex runtime 后，**内层 Agent Loop 从 Pi 切换为 Codex App Server**；OpenClaw 保留外层编排与平台控制能力。这是双层循环协作，而不是整个系统都迁移进 Codex
- openClaw 把“运行时”和“平台层”分开。默认 Pi runtime 时，Pi 同时负责会话 Agent Loop 和上下文压缩；切到 Codex Harness 后，这两项都转交给 Codex App Server。OpenClaw 不再参与压缩算法本身，而是保存渠道侧会话镜像、处理超时/取消、维护权限和动态工具桥接。`MEMORY.md`、memory flush、工具结果截断则仍属于 OpenClaw 的外围记忆与上下文治理，不能和 Codex 的 thread compaction 混为一谈

#### 三、openclaw 支持替换 agent runtime 的架构设计

OpenClaw 的核心设计不是绑定某个 Agent 框架，而是把 Agent Runtime 提升为一级抽象。平台层统一负责渠道、会话、记忆、工具治理与权限；Runtime 通过 Harness 契约负责 Agent Loop、原生工具和上下文压缩。这样既能接入 Codex 这类具备原生线程和代码工具生态的执行引擎，又避免将渠道和企业控制能力复制进每个 Runtime。关键难点不在“能否换 Runtime”，而在能力协商、双会话绑定、失败闭环和避免跨 Runtime 的语义降级。

#### 四、具体用的 codex 什么形态
OpenClaw 的 Codex Harness 不是直接调 OpenAI Responses API，也不是嵌入 Codex SDK；它启动并通过 stdio 驱动 Codex App Server。默认二进制由插件管理，默认 Codex Home 按 OpenClaw Agent 隔离。只有显式设置 `homeScope: "user"` 时，才与操作者本机 Codex CLI/Desktop 共享 `~/.codex` 的原生状态

SDK 是方便业务代码调用 Codex 的高层包装；App Server 是供 OpenClaw、IDE 这类宿主深度接管 Codex 生命周期的底层双向协议。OpenClaw 选择后者，是为了保留平台层的渠道、工具、权限和会话治理能力

```
OpenClaw 当前方式
OpenClaw ── stdin/stdout 的 JSON-RPC ──> Codex App Server 子进程

使用 SDK 的方式
你的 Node/Python 代码 ──> Codex SDK ──> Codex 运行时 / App Server ──> Codex
```
本质上 SDK 和 OpenClaw 都是运行的 Codex App Server 进程