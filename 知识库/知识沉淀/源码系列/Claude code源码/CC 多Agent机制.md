## 一、为什么需要 Mutil-Agent

- **第一，上下文会爆炸**。既要多方调研多个方案又需要执行方案编写
- **第二，职责混乱**。一个 agent 即当评审者也当程序员
- **第三，没法并发**，一个 agent 一次只能做一件事

## 二、Mutil-Agent 三种常见形态

- **第一种，父子型**。主 agent 处理整个任务，遇到某个子问题时派一个 subagent 出去搞定，拿结果回来接着干
- **第二种，平级协作型**。几个 agent 职责对等，通过共享状态或者消息互相协作
- **第三种，主从型**。一个专门的「协调者 agent」，**它自己不干活，只负责派 worker、收结果、做合成**。worker 之间互不通信，全靠协调者调度。这种是高并发场景的标配。
Claude Code 源码里，**常规 Subagent** 对应父子型，**Coordinator 模式**对应主从型，**Fork Subagent** 是父子型的一个特殊优化版本

## 三、SubAgent 的隔离机制
#### 3.1 隔离的目的
- 防止子 agent 污染父 agent 的状态。例如：修改父 agent任务表、更新读取文件的缓存
- 防止子 agent 调用不该调用的工具。例如：子 agent 调用创建 子agent 的工具，导致 agent 嵌套
#### 3.2 两个隔离的维度
##### 3.2.1  **上下文隔离**（重点）
Claude code 主 agent 与子 agent 的上下文即不是完全共享也不是完全隔离，原因在于两个极端都存在问题，举例：
- **完全共享的劣势**：子 agent 的操作污染父 agent 的视图。父 agent 已经读过 file.ts 的前 100 行，子 agent 拿过去接着读到 200 行。这下父 agent 那边「文件读到哪了」的缓存被刷成 200 了，下次它要读这文件就以为自己已经读过 200 行了，直接跳过
- **完全新建的劣势**：子 agent 跟主 agent 完全脱节。用户按 Ctrl+C 想中止整个任务，主线程把中止信号广播出去，结果子 agent 因为是全新上下文收不到这个信号，对外面发生啥一无所知，自顾自继续跑
Claude Code 采取了四个决策来折中处理：
**决策一：「读文件的缓存」要复制一份给子 agent**
- 这个缓存存的是「这个文件读过没、读到第几行」。如果父子共享，子 agent 读了某个文件，父 agent 会误以为自己也读过，下次跳过不读，数据就错了。所以要复制一份独立的给子 agent，子 agent怎么折腾都不影响父的文件视图

**决策二：「改全局状态」这件事对子 agent 直接关闭**
- 全局 UI 状态是主线程用 React 在管的，如果异步 subagent 也能改，就会出现「两边同时改同一份状态、抢起来对不上」的问题，界面就乱了。所以 Claude Code 干脆把 subagent 的「写全局状态」这个权力**完全关闭掉**，改成空操作

**决策三：「注册后台任务」这条通路得保留**
- 既然子 agent 的写权力关掉了，那它自己起的后台进程（比如在后台跑一条 bash 命令）怎么登记到全局任务表？
- Claude Code 专门开了一个**小口子**：其他写全局的口都堵死，唯独「注册/结束后台任务」这条路留着。不然子 agent 起的后台进程就变成「没爹的孤儿进程」，永远在后台跑没人回收

**决策四：给每个 subagent 发独立 ID、深度代代 +1**
- 派一个 subagent，都给它一个独立的 ID，并且在父 agent 的深度基础上 +1，这样系统能随时知道「当前这个 agent 处于嵌套的第几层」。深度超过阈值（比如 5 层）就报警甚至强制停止，防止意外嵌套失控。**源码显示仅在 Claude code 内部员工可使用子 agent 创建孙 agent（`USER_TYPE === "ant"`）**

##### 3.2.2 工具隔离三道门禁
**第一道所有 subAgent 的通用黑名单**：
- 能派新 subagent 的工具：防止子再派孙递归嵌套，工具名：`Agent`
- 能主动问用户问题的工具：子 agent 不该抢主 agent 的对话权，工具名：`AskUserQuestion
- 能切换规划模式的工具：规划模式是主 agent 用于和用户对齐方案，工具名：`EnterPlanMode`
- 能停止其他任务的工具：任务管理是主 agent 的专属能力名，工具名：`TaskStop`

**第二道是「自定义 agent 多套一层黑名单」**：当前源码保留了“自定义 agent 可额外收紧工具权限”的扩展位，但当前版本没有配置额外黑名单；

**第三道门反过来，「后台异步 agent 走白名单」**：是指这类后台 agent 仅仅能只用事先圈定好的一小批工具（例如：读文件、搜代码、执行命令等）

## 四、父子 agent 通信机制

#### 4.1 假设使用函数进行父子通信存在的弊端
- **同步阻塞**：子 agent 干活的时候父 agent 啥也做不了，只能阻塞等待
- **并发设计**：假设需要多个子 agent 同时干活时，需要设计并发方案

#### 4.2 Claude code 选择消息队列+异步通知

**首先确定子 agent 的数据结构**

```typescript
export type LocalAgentTaskState = TaskStateBase & {  
  type: 'local_agent';  
  agentId: string;               // 子 agent 唯一 ID  
  prompt: string;                // 初始任务  
  agentType: string;  
  status: TaskStatus;            // pending/running/completed/failed/killed  
  result?: AgentToolResult;      // 完成后的结果  
  progress?: AgentProgress;      // 进度  
  isBackgrounded: boolean;       // 是否已转后台  
  pendingMessages: string[];     // 信箱：父 agent 扔进来的待处理消息  
  messages?: Message[];  
};

```
- agentId：是子 agent 的唯一标识
- pendingMessages：父 agent 给子 agent 派发的任务数组

**然后确定父->子通信逻辑**
- **第一步：父 agent 往子 agent 信箱扔字条**：父 agent 调用 sendMessage 工具，往子 agent 的pendingMessages 末尾追加一条消息
- **第二步：子在循环边界自己捡字条**：子 agent 在每轮**工具调用结束**后，去的pendingMessages 中获取新消息，把新消息作为「用户消息」注入自己的对话历史中，然后开始下一轮 LLM 调用
- **特殊场景子 agent 停止运行时**：从磁盘上那份已经保存的对话 transcript 里，把子 agent 的完整对话历史恢复出来，拼上新消息，让子 agent重新跑起来

**最后确定子->父通信逻辑**
**核心思路**：子 agent 将完成的内容，拼成一段 XML，伪装成一条用户消息，塞给父 agent 的对话历史。它伪装成用户消息，**天然地复用了 agentic loop 的处理逻辑**。父 agent 不需要额外的状态机去「等通知」，它就像收到一条新的用户输入一样处理。（**非常好的设计点**）

**总结**
- 实际子 agent 运行时，默认是**前台模式**，当处于前台模式时，主 agent 会阻塞等待子 agent 返回结果。通过配置环境变量CLAUDE_AUTO_BACKGROUND_TASKS 可设置自动**前台转后台模式**，当处于自动转后台模式时，主 agent 最多阻塞等待 2 分钟，2 分钟子 agent 仍为返回内容，将其切换为后台模式，此时子 agent 完成任务后会采用子->父通信逻辑。**后台模式**：主agent不等待，发完消息直接走。关于如何触发后台模式：1.模型调用时显示指定后台运行子agent；2.自定义agent中定义固定后台运行；3.满足前台转后台条件
## 五、Fork Subagent 省钱又省延迟的隐藏大招
#### 5.1 背景介绍
Claude code 的 system prompt 长度是**上万 Token**，里面塞了大量的工具说明、规范约定、用户上下文。
假设每派一个 subagent，如果它有独立的 system prompt（内置的 Explore、Plan 这些都有独立的），LLM API 那边就得**对这一万多 token 重新从头算一遍**，这有两个代价：**钱**（input token 重新算钱）和**延迟**（首 token 等更久）

Anthropic 有个 **prompt 缓存**机制可以缓解这事。简单说：**API 请求里如果前缀跟之前某次请求一样，这段前缀可以不重新算，直接走缓存，价钱只要原来的 10%，延迟也大幅降低**。

**如何命中缓存**：字节级完全相同，才能命中缓存

#### 5.2 Fork 的核心思路
通过五项内容，保证子 agent 发出 prompt 和父 agent 一致，最大程度利用缓存机制
- **系统 prompt 的内容**（最核心的，对齐第一位）
- **用户上下文**（拼在消息前的那部分动态内容，比如CLAUDE.md 、记忆文件）
- **系统上下文**（拼在 system prompt 后的环境信息，例如：Git 快照、Agent 行为规则）
- **工具池的顺序和定义**（工具的字段结构会被序列化进 API 请求，顺序都不能变。**但仍然会过滤掉子 agent 不能使用的工具**）
- **对话历史的前缀**（决定了 user/assistant 消息序列中「从哪里开始分叉」

## 六、Coordinator 模式：真正的多 Agent 并行协作
#### 6.1 Coordinator 核心设计
Coordinator 模式下，主 agent 不干实际工作了，它只做三件事：**派 worker、收结果、合成答案**
```json
You are Claude Code, an AI assistant that orchestrates software engineering   
tasks across multiple workers.  
  
## 1. Your Role  
You are a **coordinator**. Your job is to:  
- Help the user achieve their goal  
- Direct workers to research, implement and verify code changes  
- Synthesize results and communicate with the user  
- Answer questions directly when possible, don't delegate work   
  that you can handle without tools

简单翻译：你的身份是协调者，你的工作是指挥 worker 去做研究、实现、验证，然后自己合成结果跟用户交流。能自己回答的问题不要派人去做
```
**开启条件**：默认是关闭的，使用/coordinator 或设置环境变量 `CLAUDE_CODE_COORDINATOR_MODE=1` 启动

```
启动 Claude Code
-> 输入 /coordinator
-> 主 agent 变成 Coordinator
-> 它只能使用 Agent / SendMessage / TaskStop 等编排工具
-> 用 worker agent 做读、写、测试等实际工作
```
#### 6.2 Coordinator 能运转的核心工具箱
- **派 worker 的工具**：派一个新 worker 出去干某件具体的活，派完立刻返回 worker 的 ID
- **创建/解散团队的工具**：批量管理 worker 组
- **给 worker 发消息的工具**：给已经派出去的 worker 发后续指令（也就是前面讲的 SendMessage），因为 worker 的上下文还在，续命比重新派一个更省钱
- **合成最终输出的工具**：协调者合成完答案后，通过这个工具把最终回复交给用户
- **停止 worker 的工具**：当协调者意识到某个 worker 跑错方向时，把它停掉省 token

**Coordinator 并行的秘诀，给主 agent 设置并发提示词**

```json
Parallelism is your superpower. Workers are async. Launch independent workers concurrently whenever possible, don't serialize work that can run simultaneously and look for opportunities to fan out.

翻译：并行是你的超能力，worker 全是异步的，能并行的绝不串行，多找机会一口气派一堆出去
```
#### 6.3 Coordinator 模式的工程启示
**第一，角色分离**。协调和干活是两件事，不要让同一个 agent 身兼二职。角色清晰的系统更稳定。

**第二，并发优先**。异步 + 消息队列是并发的基础，有了这套基础，多 agent 才能真正发挥威力。

**第三，合成不转发**。协调者要理解中间结果，不能把它当传话筒。这是 Multi-Agent 系统里最容易踩坑的一点。

**第四，扁平不递归**。通过工具权限把层级限制在两层（协调者 + worker），避免失控的递归嵌套。

## 七、五条 Mutil-agent 设计原则

##### 原则 1: 上下文隔离要按字段粒度做
##### 原则 2：通信走消息，不走函数调用
##### 原则 3：工具权限要分级管控
##### 原则 4：缓存友好是一种架构能力
##### 原则 5：并行优先 + 协调者合成

## 八、三种 agent 模式适用的场景
| 模式            | 最适合的场景                               | 典型例子                                            |
| ------------- | ------------------------------------ | ----------------------------------------------- |
| 父子 Agent      | 任务边界清晰，主 agent 需要拿到结果后才能继续决策         | “扫描认证模块，找出权限校验入口并汇报”；“审查这次改动的潜在回归”              |
| Fork Subagent | 多个任务依赖当前完整对话、已读文件和已有推理，需要从同一上下文点并行分叉 | 已完成架构阅读后，同时分叉：一个查 bug 根因、一个评估改法、一个找测试缺口         |
| Coordinator   | 大型、多阶段、可并行的工程任务，需要持续拆解、追踪、汇总和调整分工    | “重构支付模块：先调研，再设计，再分模块实现，再跑测试和审查”；“并行排查多个服务的线上问题” |
## 九、CC 定义的六类子 agent 类型
| 类型名 `subagent_type` | 作用                                         | 工具差异 |
| ------------------- | ------------------------------------------ | ---- |
| `general-purpose`   |                                            |      |
| `statusline-setup`  | 专门配置 Claude Code 状态栏                       |      |
| ``                  | 只读代码探索、定位文件和调用链、收集事实                       |      |
| ``                  | 架构设计和实施计划，输出步骤、关键文件、权衡                     |      |
| `claude-code-guide` | 回答 Claude Code、Agent SDK、Claude API 相关使用问题 |      |
| `verification`      | 对已完成改动做验证、测试和对抗性检查                         |      |
| `worker`            | Coordinator 模式下的实际执行 worker，可调研、实现、验证      |      |
- **general-purpose** 
	- 角色：通用调研、搜索、执行多步骤任务；要求完成任务后简洁汇报
	- 工具差异：排除子 agent 不能使用的工具，其余都能使用
	- 上下文差异：只拿任务 prompt，不继承父 transcript
- **Explore**
	- 角色：**只读代码检索专家**，强调快速搜索、分析、报告
	- 工具差异：禁止 `Agent`、`ExitPlanMode`、`Edit`、`Write`
	- 上下文差异：默认去掉 `CLAUDE.md` 和 Git 快照，降低 token 成本
- **Plan**
	- 角色：软件架构师：调研后产出实施步骤、关键文件、依赖和风险
	- 工具差异：禁止 `Agent`、`ExitPlanMode`、`Edit`、`Write`
	- 上下文差异：默认去掉 `CLAUDE.md` 和 Git 快照，降低 token 成本
- **verification**
	- 角色：对已完成改动做验证、测试和对抗性检查
	- 工具差异：禁止直接 `Edit`、`Write`、`NotebookEdit`、嵌套 agent、退出计划模式
	- 上下文差异：普通子 agent 上下文；另有每轮重申的 verification-only reminder
- **worker**
	- 角色：Coordinator 的执行单元：调研、实现、测试并汇报
	- 工具差异：`ASYNC_AGENT_ALLOWED_TOOLS`，即 Read、Glob、Grep、Bash、Edit、Write、Skill 等后台安全工具；**去掉协调工具**
	- 上下文差异：不继承 Coordinator 的完整历史，依赖 Coordinator 在任务 prompt 中写清楚
- **fork**
	-  角色：没有自己的有效 system prompt，直接继承父 agent 已渲染的 prompt
	-  工具差异：继承父 agent 的精确工具 schema，再移除子 agent 禁用工具
	-  上下文差异：继承父 agent 当前完整 transcript 快照