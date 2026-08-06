## 一、四层记忆分层
- **第一层：身份/行为上下文**
	- **存储的内容**：Agent 人设、用户画像、规则、工具备注
	- **代表文件**：例如：AGENTS.md、`SOUL.md`、`IDENTITY.md`、`USER.md`、`TOOLS.md`、`HEARTBEAT.md`、`BOOTSTRAP.md` 。落盘位置：工作区根目录 Markdown
	- **如何进入模型上下文**：启动时作为 bootstrap 文件注入
- **第二层：长期记忆**
	- **存储的内容**：决策、偏好、稳定事实
	- **代表文件**：`MEMORY.md`、`memory/**/*.md`
	- **如何进入模型上下文**：基于 SQlite 数据库，即对两类文件向量化也存储原文。通过向量化检索（约 400 token 切块，80 token overlap）和全文检索进行检索，默认返回最多 6 条，采用混合检索，向量权重 0.7、全文 FTS 权重 **0.3**。<font color="#c0504d">并且进行记忆检索时阻塞主 Loop 进程的，这与 Claude code 的异步检索记忆机制完全不同</font>
	- **<font font-weight="blob" color="#c0504d">何时调用长期记忆</font>**：系统 prompt 提示模型在涉及旧决策、人物、偏好、待办、日期等问题时先搜索。因此是由模型自主决策是否调用记忆检索工具
	- **检索细节**：在bootstrap 总字符不超过150,000 时（即 AGENT.md、SOUL.md 等文件字符合集），`MEMORY.md` 在不超过 20000 字符会全量注入bootstrap，假设超过则取其头和尾凑齐 20000 字符
	- `MEMORY.md` 与 `memory/**/*.md` 是“长期精炼层 + 明细记录层”的约定，没有索引之间的关系
- **第三层：会话历史**
	- **存储的内容**：每轮原始消息、工具调用、压缩摘要
	- **代表文件**：`~/.openclaw/agents/<agentId>/sessions/*.jsonl`
	- **何时进入模型上下文**：恢复同一 session 时
- **第四层：检索索引**
	- **存储的内容**：Markdown 切块、embedding、FTS 元数据
	- **代表文件**：`~/.openclaw/memory/<agentId>.sqlite`
	- **何时注入模型上下文**：不直接注入；供搜索工具使用，也就是对第二层进行检索时被使用

## 二、如何存储记忆
- **模型存储长期记忆文件**：模型将认为值得长期保存的信息写入 `MEMORY.md` 或当天的 `memory/YYYY-MM-DD.md`
- **模型写入长期身份信息文件**：默认会询问用户、自动识别身份信息等写入SOUL.md 、`USER.md` 等文件
- **存储历史对话**：将历史对话内容存储在 JSONL 文件中

## 三、压缩上下文及阈值
- **会话压缩**：compaction 由 Pi Agent SDK 执行：到阈值后总结较早历史，并保留最近的 `keepRecentTokens`（20000 tokens）
- **长期记忆沉淀（memory flush）**：在压缩前让模型把重要事实写进 Markdown，避免仅存在于会话摘要中
- **压缩阈值**：openclaw 默认是保留 200 K，即模型上下文窗口只剩下最后 200 K 时开启压缩
- **轻量裁剪**：仅在发送给 LLM 前，裁剪旧工具结果以减少 token。启用 `cache-ttl` 模式后，默认在上下文达到 30% 时截断工具输出，达到 50% 时可清空旧工具输出；保留最近 3 个 assistant turn。但需要用户手动配置。**仅对支持prompt-cache TTL（Time To Live 存活时间） 的供应商提供，例如 Anthropic 的最大缓存时间是 1h，那么在 1 h 之前的工具调用结果，openclaw 就能去掉以此来节约上下文**
## 四、多人同时使用 openclaw 如何隔离

- **方案一：相同Agent、按 session 隔离**
	- **已隔离信息**：
		- 每个 session 有自己的 JSONL 对话上下文、包括 token 用量、压缩次数、模型/思考档位等 session 状态
	- **未隔离信息**：
		- 相同 session 具备同一个 workspace: `MEMORY.md` 、`memory/**/*.md` 、`AGENTS.md`、`SOUL.md`、`USER.md`、`IDENTITY.md`、`TOOLS.md` 等文件共享
		- SQLite 记忆索引、记忆向量检索
	- **存在的问题**：个性化记忆串人、语义检索跨用户命中、共享 bootstrap 造成隐私泄露
	- **适合场景**：同一个团队共用一个公共助理
		- 记忆本来就应共享，例如项目状态、团队流程、产品知识
		- 每个用户只需隔离聊天上下文，不要求隔离长期资料
		- 不把个人隐私、个人画像写入共享 `USER.md` / `MEMORY.md`
- **方案二：按用户维度创建 agent**
	- **隔离信息**：所有信息都隔离
	- **未隔离信息**：所有用户共享一个 gateway 进程，同一个进程
	- **使用方法**：`agents.list` 创建多个 Agent，再用 `bindings` 把不同渠道账号、用户或群路由到对应 Agent
- **方案三：企业级维度每人部署一个 Gateway 实例**
	- **隔离信息**：所有信息进程级别隔离，重启互不影响
	- **典型的云端部署场景不是一人一台服务器**：
		- 多台物理机组成 Kubernetes 集群。
		- 每个用户运行一个 Pod 或容器，容器内运行一个 OpenClaw Gateway。
		- 每个用户挂载一份独立持久卷，例如 PVC；容器重启、升级、迁移到另一台机器后，记忆和会话仍在。
		- 所有 Gateway 在容器内只监听本地端口；用户访问统一的 HTTPS 域名，由反向代理根据登录用户把请求转发到对应 Gateway。
		- 控制平面负责创建用户运行时、记录“用户 ID → Pod/实例”的映射、健康检查、休眠和唤醒
