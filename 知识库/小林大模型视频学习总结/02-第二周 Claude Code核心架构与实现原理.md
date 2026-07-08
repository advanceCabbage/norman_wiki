## 一、CC定义
CC是Anthropic官方的AI编程CLI，它的本质是一个tool-use agent loop：模型读代码、改文件、跑命令、自主决策，循环往复直到任务完成
## 二、记录
- 多个工具执行时，如何处理？例如网络工具耗时长，bash工具耗时短，如何定义多个工具的执行顺序？是否需要等待所有工具返回结果？
	- 基础Bash工具是默认注入的
	- 网络类的工具是仅注册未加载依赖，使用到时再加载依赖
	- Team agent中子agent用到时对应的工具才加载
	- 工具本身有定义是否允许并发执行
- agent Team中如何分发子任务
## 三、工具系统[[Claude Code工具|工具系统详细解释文章]]
- 确保工具安全执行，Hook + 权限执行栈
	- **Hook是工具执行内容维度**。工具调用之前，添加Hook。阻止在工具执行之前，是通过工具执行的内容为判断标准，判断改内容是否有风险，是否允许执行，举例：判断工具的执行内容是否包含rm -rf
	- Claude Code 支持的所有 Hooks 有哪些
	- **Permission是工具维度**。Permission Check 设置系统内白名单，按照工具维度设置：1. 工具执行是否需要向人确认 2. 该工具是否允许并发
- 基础工具：Bash 、 Read、Edit、Write、Glob、Grep。本质上都是Bash工具，按照权限分裂出了其他工具，方便鉴权
- Skill：Skill本质是作为agent loop中的tool加载的，Skill渐进式披露加载的过程本质上是子agent按照上下文加载，并将加载的上下文内容返回给主控agent [[你不知道的 skill 规则，对比 Claude code 和 Codex 中 skill 的差异]]
- 如何提升工具调用的准确度
	- 系统提示词写的好，添加全局说明，例如说明什么情况下使用read，工具如何协作
	- 工具描述本身，工具的说明需要准确，什么时候使用，需要传入哪些必填参数
	- skill注入，把工具的调用链路封装为统一的方式。
	- 模型微调
- 流式工具执行
	- 直接安全的并发执行
	- 有依赖的进入安全队列，顺序执行
## 四、记忆系统 [[🧠 Claude Code 记忆机制（微信公众号版）]]
- 记忆是什么结构、如何写入、如何取
	- 显式记忆：用户说「记住这个XXX」或模型判断信息值得保存  ->  按prompt指令直接Write工具操作文件，写内容文件、更新索引
	- 隐式记忆：REPL每轮结束 -> 后台asyncio任务 ->  独立API调用分析对话 ->  自动提取保存
- 四种记忆类型
	- User 用户身份：用户角色、目标、指责
	- feedback：用户行为反馈
	- project ：项目上下文
	- reference ：外部引用：了解到外部系统中资源的位置和用途，只存位置，不存内容
- 信任但验证 ：「记忆说X存在」 不等于 「X现在存在」
- Plan和Task的分工
	- 何时用Plan而非Memory：即将开始非简单的实现任务、想与用户对齐方案是 -> 用Plan
	- 何时用 Task而非Memory：需要将工作分解为步骤、追踪进度是 -> 用Task
	- 核心判断：如果信息只在当前会话有用，它不属于Memory
- 后台保存记忆专用指令
	- 保存记忆类型：User、feedback、project、reference
	- **核心提示词**：你是一个记忆提取agent。分析下面的对话，判断是否有值得保存到持久化记忆中的内容。要非常有选择性，大多数轮次没有值得保存的内容，永远不要保存 API key、密码或凭证。输出格式严格 JSON，可用 json.loads 直接解析。
- memory何时存储的
## 五、完整 runtime 逐步追踪，十二个步骤
- 第一步用户输入（System prompt组装）：身份与安全、系统行为与契约、任务执行原则、任务谨慎原则、工具使用规范、语气与风格、输出效率、环境信息、工具结果摘要提示、记忆系统、CLAUDE.md
- **为什么CLAUDE.md的执行等级越高？原因是最晚加载的提示词权重最高，优先级最高。**
- 第二步 追加message：将用户的输入追加到系统提示词后
- 第三步 normalize：保证输入信息的结构正确，例如：保证一条user消息，一条assistant助手消息结构
- 第四步 Token估算：Token是否超过阈值，自动压缩
- 第五步 call_model：将消息发送到大模型 API
- 第六步 SSE流式返回
- 第七步 工具执行：Hook + Permission check ，再执行工具，校验工具执行的结果是否安全
- 第八步 落账点1 Assistant ：获取工具写入上下文
- 第九步 落账点2  Tool Result：工具执行结果写入上下文
- 第十步 第二轮 normalize + call_model
- 第十一步 无工具调用时，返回大模型内容给用户
- 第十二步 后处理：会话持久化、Token累计、后台记忆提取（异步将有用的信息存入记忆系统）
## 六、Agent Teams
#### 6.1 什么时候触发多Agent协作？
多 Agent 协作不是系统自动强制触发的，而是由主模型根据任务的复杂度和可用工具，自主决定是否调用 Agent 这类协作工具。

当任务比较复杂，比如需要跨文件调研、并行搜索实现和验证，可以拆开；或者主 Agent 希望把某个子任务委派出去时，它可以调用Agent来创建子 Agent 

另外，系统也支持 coordinator 模式。开启 coordinator 模式后，主协程的系统提示词会变成协调者角色，它会更主动地拆分任务、并行派发 worker、收集结果并综合回答。

·所以触发条件可以总结为两类：
1. **普通模式下**，模型主动调用 agent 的工具触发
2.  **coordinator 模式下**，系统提示词引导主 agent 更倾向于使用多 agent编排

**如何开启 coordinator 模式？**
- 在当前shell中设置 CLAUDE_CODE_COORDINATOR_MODE
```
export CLAUDE_CODE_COORDINATOR_MODE=1
```
- 对当前启动命令生效
```
CLAUDE_CODE_COORDINATOR_MODE=1 python -m cc
```
在多 Agent 协作模式下，主 Agent 会被注入一段 Coordinator System Prompt。这个 Prompt 会把主 Agent 的角色从普通执行者转变为协调者。

其职责不再是由其亲自完成所有事情，而是：
1. 判断哪些任务适合自己直接完成；
2. 判断哪些任务应该拆分给 Worker Agent；
3. 负责汇总 Worker 的结果；
4. 继续派发后续任务；
5. 处理失败和验证结果。
#### 6.2 主 agent和子 Agent的如何协作？
主 Agent 和子 Agent 的协作本质是**任务委派+结果回传**。

主 Agent会给子 Agent一个明确的 prompt，这个 prompt 必须尽量自包含，因为子 Agent默认看不到主  Agent和用户之间的完整对话。子 Agent拿到任务后会启动自己的执行循环，独立调用模型，使用工具读取或修改文件，直到任务完成。

子 Agent完成时，会把结果以文本形式返回给主 Agent。对于主 Agent而言，这个结果就像一次工具调用的结果。主 Agent会基于这个结果继续推理、汇总，并决定：
1. 是否继续追问细节；
2. 或者把结果反馈给用户。

如果是后台子 Agent的，主 Agent 不会阻塞等待，而是先拿到一个任务 ID，子 Agent在后台运行，完成后再通过任务结果或通知机制回到主 Agent的上下文中。

一句话总结：主 Agent负责拆分任务、下指令、综合结果，子 Agent 负责独立执行具体的任务。
#### 6.3 多agent在同一进程内如何互不干扰？
主要靠**五层隔离**：

- **第一是对话上下文隔离**：每个子 Agent 都有自己的 message 列表，不会产生污染主 Agent 的 transcript，主 Agent 只拿到子 Agent 最终结果

- **第二是工具级隔离**：子 Agent 会从父 Agent 继承工具，但会过滤掉一些不适合子 Agent使用的工具，比如: 防止它继续无限递归创建新的 Agent、或者后台 Agent不能再使用需要用户交互的工具

- **第三是身份隔离**: 如果是同进程 teammate 这种模式，会类似于协程本地变量的机制来保证每个 agent 的身份，比如 agent  ID、team name、agent name。这样多个 agent 即使运行在同一个进程和事件循环里，也能知道“自己是谁”、“属于哪个团队”，不会串身份。

- **第四是任务状态隔离**：后台 Agent 会被注册成独立的任务，每个任务都有自己的 task ID、状态、元信息和异步任务引用，因此可以单独查询、停止、恢复状态

- **第五是工作目录隔离的设计**。通过 Git worktree 隔离子 Agent 修改的设计思路，用来避免多个 Agent 并行修改同一个目录，防止互相覆盖
#### 6.4 子agent如何被创建和执行
**创建子Agent有四步**：

- **第一是主Agent调用Agent工具**：并传入任务 Prompt 、描述、是否后台运行、模型选择等参数

- **第二是系统为子 Agent 创建了一个独立的运行环境**：包括： 独立的 message、独立的工具注册表、默认的子 Agent system prompt、权限检查器、以及模型调用函数

- **第三是系统启动子Agent的 loop**：前台模式下：主任务等待子任务跑完、后台模式下：系统将子任务包装成异步任务，放入后台任务管理器运行，并立即返回任务 ID。

- **第四是子 Agent 执行完后**：把输出汇总为文本结果。前台模式直接作为工具结果返回；后台模式通过任务管理或通知机制让主 Agent 后续感知结果

所以它不是开一个完全独立的大程序，而是在当前运行时里创建一个独立上下文，让它复用同一套模型调用、工具执行和 loop 机制
#### 6.5 agent loop机制
Agent loop 的核心是一个“模型调用到工具执行再回到模型”的循环。

流程可以概括为：

1. **准备上下文**：把当前 messages、system prompt、可用工具 schema 整理好。
2. **调用模型**：模型基于上下文输出文本，或者提出工具调用。
3. **解析工具调用**：如果模型产生 tool use，系统把工具调用提取出来。
4. **执行工具**：工具执行时会经过权限检查、hook、安全控制、并发控制。
5. **回填工具结果**：工具结果会作为新的 user message 放回 transcript。
6. **再次调用模型**：模型看到工具结果后继续推理。
7. **结束判断**：如果模型不再调用工具，而是正常回答，就结束本轮 loop。

主 Agent 和子 Agent 本质上都用这套 loop。区别只是主 Agent 外面还有 **REPL（Read-Eval-Print-Loop）** 循环，用户可以一轮一轮输入；子 Agent 通常只有一个初始任务 prompt，然后在内部最多跑若干轮，直到完成任务或达到最大轮数

## 七、大纲
- skill [[你不知道的 skill 规则，对比 Claude code 和 Codex 中 skill 的差异]]
- 记忆系统 [[🧠 Claude Code 记忆机制（微信公众号版）]]
- loop
- agent Teams 
- 系统提示词 [[02-Claude code提示词]]


## Claude code源码Loop流程
#### 1. 进入while（true）
每一轮代表一次“模型请求或工具回填后的继续请求”
#### 2. 准备本轮状态
取出当前 message、 toolUseContext 、 turn count、 compact 状态、错误恢复状态等
#### 3. 启动异步预取
启动 skill discover、extra tools discover、relevant  memory perfect 等异步任务，尽量和模型请求、工具执行重叠
#### 4. 截取有效上下文
从 compact boundary 之后取消息，去掉不需要再次发送给 API 的临时字段，比如旧的 toolUseResult 原始对象
#### 5. 压缩与裁剪上下文
依次执行 tool result budget、history snip、microcompact、context collapse、autocompact。必要时产出 compact boundary message
#### 6. 组装系统提示词与 tool context
合并 system prompt、system context、user context，并把当前 message 写回toolUseContext.messages
#### 7. 初始化本轮容器
创建：  
`assistantMessages`  
`toolResults`  
`toolUseBlocks`  
`needsFollowUp`  
以及可选的 `StreamingToolExecutor`
#### 8. 检查上下文是否已到 blocking limit
如果已经超过且不能自动 compact，直接返回 blocking limit
#### 9.预测性 compact
如果预测 本轮增长会超过上下文窗口，提前 compact 再继续当前请求准备
#### 10. 调用模型
通过 `deps.callModel(...)`，生产环境实际是 `queryModelWithStreaming(...)`
#### 11.解析模型流
接收 assistant message、stream event、API error message 等内部事件
#### 12.收集 assistant 消息
每个 assistant block 被加入 `assistantMessages`，并 yield 给上层 UI / SDK
#### 13. 发现 tool_use
如果 assistant content 中包含 `tool_use`，加入 `toolUseBlocks`，并设置 `needsFollowUp = true`
#### 14.可选：流式提前执行工具
如果启用 `StreamingToolExecutor`，tool_use 一出现就可以开始调度工具，不必等完整 assistant 响应结束
#### 15.处理流式 fallback / 模型 fallback
如果 streaming fallback 或 fallback model 被触发，清空本轮已收集的 assistant/tool 状态，重试模型请求
#### 16. **模型流结束后处理 API 恢复**
处理 withheld 的 `prompt_too_long`、media too large、`max_output_tokens` 等错误
#### 17.执行 PostSampling hooks
模型采样完成后执行内部 post sampling hooks，例如 session memory
#### 18. 如果用户中断补齐缺失的 tool result 后结束
防止出现 assistant 有 tool use 但没有对应的 tool result 的非法 transcript
#### 19.如果没有 tool_use
说明模型本能不需要工具进入结束 路径
#### 19.1 执行 stop hooks
Stop hooks 可阻止继续并结束，返回 blocking error，让 loop 带着错误信息继续或正常通过
#### 19.2 检查 token budget（用户指定的token预算）
如果 token budget 策略要求继续，会插入 meta user message，然后 `continue`。
举例：当模型已经没有工具调用准备结束时，检测当前的 token 消耗是否达到用户的标准，假设用户设定了 500K，如果还没达到预算的 90%，就插入一条隐藏消息，让模型保持继续工作，但是不要去做总结。**它的实际处理的任务是防止模型在长任务、深度研究、大规模分析时过早地说完成了**。但当前还是有一个防止死循环的机制。假设说，如果已经连续执行了三次，并且最近新增 token 数都小于 500，那么就认为继续也没有任何产出了，则停止继续任务。
一句话：**token budget 是“用户希望这轮多投入多少输出 token”的软目标检查器，用 meta user message 推动模型继续，而不是工具执行或 API 错误恢复机制。**
#### 19.3 无工具、无阻塞时结束
返回 `completed` 
#### 20 如果存在 tool_use，执行工具
使用流式执行器的剩余结果，或调用 `runTools(...)` 普通调度
#### 20.1 工具执行链路
每个工具依次经过：  
- input schema 校验；  
- tool validate；  
- PreToolUse hooks；  
- Permission；  
- `tool.call(...)`；  
- PostToolUse hooks；  
- 生成 `tool_result` user message
#### 20.2 收集 tool_result
工具结果被 normalize 成 API 可见的 user role 消息，加入 `toolResults`
#### 20.3 工具后注入 attachment
注入排队命令、相关 memory、动态 skill discovery、extra tools discovery 等 attachment。
#### 20.4 **刷新工具列表**
如果 MCP 或动态工具有变化，刷新 `updatedToolUseContext.options.tools`
#### 20.5 检查 maxTurns
如果下一轮超过 `maxTurns`，返回 `max_turns`
#### 20.6 构造下一轮 state
把 messagesForQuery中的 assistantMessages、toolResults作为下一轮messages
#### 20.7 continue
回到 `while (true)` 顶部，把工具结果发回模型，让模型基于结果继续推理

