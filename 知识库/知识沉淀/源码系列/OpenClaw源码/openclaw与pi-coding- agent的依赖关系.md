只看 OpenClaw 对 `@mariozechner/pi-coding-agent` 的**直接功能依赖**，它本质上把 Pi Coding Agent 当作嵌入式 Agent SDK，而不是启动 Pi CLI 子进程

```
pi-coding-agent 提供：
AgentSession(创建一次agent会话)、SessionManager（打开/创建JSONL session）、模型/认证注册、工具协议、
Skills/Extensions 资源机制、摘要与 token 估算。

OpenClaw 负责：
Gateway 和多渠道接入、会话路由与排队、工具注册和权限过滤、
沙箱、记忆、插件 Hook、长输出防护、context overflow 恢复、
最终消息渲染与发送
```

OpenClaw 并未自行实现一个完整 Agent SDK，而是以 `pi-coding-agent` 作为嵌入式运行时：通过 `createAgentSession` 获得 Agent Loop，通过 `SessionManager` 管理对话树与持久化，通过 Pi 的 ToolDefinition 接入工具，通过 Skills/Extensions/Compaction API 复用资源和上下文能力。OpenClaw 的差异化价值在于把这些通用 Agent 能力包进 Gateway 的多渠道、多租户会话、权限、沙箱、记忆和企业级可靠性控制中
