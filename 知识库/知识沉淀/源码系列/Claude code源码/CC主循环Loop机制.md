## 零、概览
Claude Code 的主循环是一个状态机。用户输入先被标准化为消息和附件，再与系统提示词、工具 schema、环境上下文一起发给模型。模型流式返回文本和工具调用；若没有工具调用，经过 Stop Hook 和 token budget 判断后结束。若有工具调用，系统依据工具的并发安全性调度执行，并在每个工具内部依次经过 schema 校验、PreToolUse Hook、Permission、tool.call、PostToolUse Hook。工具结果以 user role 的 tool_result 回填模型，同时补充 Memory、Skill、文件变更等附件，然后进入下一轮模型调用。这个循环持续到模型完成任务或系统触发终止条件
## 一、Loop 循环图谱
![[Pasted image 20260721142341.png]]

## 二、Loop 工程化设计体现
- **异步输出机制**：借助 `async generator` 实现边生成边输出。模型文本、思考、工具进度、权限请求、工具结果和压缩事件都可逐步 `yield` 给 REPL/SDK，用户无需等待整轮任务结束
- **显式状态机循环**：`query()` 用 `State` 保存 `messages`、工具上下文、压缩状态、重试次数、turn count 等，并通过 `continue` 进入下一轮。复杂任务不会散落成回调链，恢复和调试更容易
- **流式提前执行工具**：`StreamingToolExecutor` 在模型流中一收到完整 `tool_use` 就可启动工具，不必等模型整段输出结束，降低“模型输出时间 + 工具执行时间”的串行等待
- **基于风险的并发调度工具**：不是盲目 `Promise.all`。连续 `isConcurrencySafe` 工具并发，非并发安全工具独占串行，既提升 Read/Glob/Grep 等吞吐，也避免 Edit/Write/Bash 等竞争条件
- **工具执行管线标准化**：所有工具经过统一链路：schema 校验、PreToolUse Hook、Permission、`tool.call()`、PostToolUse Hook、结果映射。新增工具能自动获得权限、Hook、审计和错误处理能力
- **权限与模型决策分离**：模型只能提出工具调用，不能直接获得执行权。真正的写文件、执行命令等操作由 Permission 的 `allow / ask / deny` 强制控制，避免把 prompt 当作安全边界
- **上下文生命周期管理**：在每轮调用前做 tool result budget、microcompact、snip、auto compact；压缩后用摘要替代旧历史，并重新注入 Skill、Plan、近期文件等关键状态，支持长任务持续运行
- **可恢复性设计**：用户消息先持久化到 transcript；compact boundary 记录上下文切分点；文件编辑前有 file history 备份。即使进程中断，也能 resume，会话和代码都不至于直接丢失
- **分层错误恢复**：面对模型 fallback、`max_output_tokens`、`prompt_too_long`、工具失败、用户中断等情况，不是立即整体失败，而是分别重试、续写、压缩、回填错误结果或安全退出
- **防止无限重试的熔断机制**：自动压缩连续失败达到阈值后停止重试；`max_output_tokens` 也有恢复次数上限。这避免上下文已不可恢复时反复发送注定失败的请求
- **Hook 扩展点完整**：用户可以在用户输入、工具前后、工具失败、Stop、Compact、SessionStart 等阶段介入，不需要修改主循环代码即可加入企业策略、审计、上下文或工作流
- **后台任务与主会话隔离**：Memory 提取、Prompt Suggestion、工具摘要、子 Agent 等辅助任务可异步运行，主循环只在需要时消费结果，避免把所有辅助能力都阻塞在关键路径上
