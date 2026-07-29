#### 一、gateway 层面的两类权限管理
- `operator.admin`，位于Gateway 控制面，可改配置、管理 Agent、安装 Skill、重置 session、直接写受控 Agent 文件
- `node`，已配对设备，如 macOS/iOS/Android 节点，只处理节点专属 RPC，例如执行 Gateway 下发的节点命令、上报能力

#### 二、聊天层面的三类权限管理
- **chat-admin**（owner）：发送者命中 owner allowlist，具备基础 Tool 集 + owner-only Tool（Gateway 管理类工具、定时任务管理、WhatsApp 登录流程）
- **user**：消息已被渠道/群组策略放行，但不是 owner，具备基础 Tool 集 
- **guest**：未通过 DM pairing、DM allowlist、群组 allowlist 等入口策略，不能驱动 agent

修改 USER.md 等文件是由模型驱动的，因此 owner、user 都有可能修改该文件。

#### 三、Tool 的权限控制
- `owner-only` Tool：仅渠道 owner 可见/可用；
- 子 Agent：默认禁止 gateway、cron、memory、直接 `sessions_send` 等系统级能力；叶子子 Agent 还禁止 spawn 和 session 管理能力；
- 可选插件 Tool：默认不加载，必须显式被 allowlist 命中；
- Tool hook：`before_tool_call` 可以拦截或改写参数，`after_tool_call` 做审计/观测；
- HTTP `/tools/invoke`：即使通过 Gateway token，也会复用 Agent 工具策略，并额外默认拒绝 `sessions_spawn`、`sessions_send`、`gateway`、`whatsapp_login`。