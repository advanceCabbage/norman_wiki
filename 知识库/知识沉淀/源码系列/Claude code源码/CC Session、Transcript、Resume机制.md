#### 一、用户消息、助手消息、工具调用、工具结果分别何时持久化？
| 内容   | 载体                                          | 持久化时机                                |
| ---- | ------------------------------------------- | ------------------------------------ |
| 用户消息 | `user` message                              | 接受输入后、发 API 请求前                      |
| 助手消息 | `assistant` message                         | 流式响应形成 assistant 内容块并加入 `messages` 后 |
| 工具调用 | assistant 的 `content[].type === "tool_use"` | 随对应 assistant message 一起落盘           |
| 工具结果 | user 的 `content[].type === "tool_result"`   | 工具执行完成、结果回填为 user message 后落盘        |

#### 二、进程重启后，`resume` 如何恢复消息、compact boundary、已调用 Skill、子 Agent 状态？
- **恢复主会话上下文**：它从 JSONL transcript（通常存储位置：~/.claude/projects/-Users-haoyang-Documents-claude-code/sessionId.jsonl
） 读取消息，找到最新的主会话叶子节点，沿 `parentUuid` 重建有效消息链。若发生过 compact，则按 `compact_boundary` 跳过已被摘要替代的旧上下文，只恢复“摘要 + 边界后的有效消息 + 必要保留片段”
- **恢复会话附属状态**:除消息外，还会恢复文件历史快照、已读文件状态、会话标题、标签、主 Agent 配置、运行模式、worktree、目标状态等
- **恢复 Skill 与子 Agent 的可续状态，但范围有限**。已加载的 Skill 正文通常已作为会话消息存在；子 Agent 方面，本地子 Agent 可以显式恢复


#### 三、 `resume`、`compact`、`clear` 三者分别改变什么，哪些数据始终保留？
| 操作        | 改变什么                                                     | transcript / 历史是否删除                        |
| --------- | -------------------------------------------------------- | ------------------------------------------ |
| `resume`  | 切回原 session ID，恢复有效消息链、文件历史、agent/worktree/mode 等元数据     | 不删除；在原会话上继续追加                              |
| `compact` | 内存中的 model context 改为 `boundary + summary + 保留消息 + 必要附件` | 不物理删除旧 JSONL 行；追加 boundary，读时截断旧链          |
| `clear`   | 清空当前内存消息、会话缓存、文件历史状态，生成新的 session ID                     | 不删除旧 session 文件；新 session 从新 transcript 开始 |
#### 四、为什么 transcript 是完整事实记录，而 model-facing context 可以是压缩后的投影？
- transcript 是**追加式的持久会话记录**
- compact 不会回写并篡改旧消息。它追加一个新的 `compact_boundary` 与摘要；恢复/发送模型前，再从最新有效叶子沿 parent 链重建
这样分层的工程收益是：
- **模型上下文可控**：只发送摘要与近期有效信息，节省 token。
- **持久记录可追溯**：旧消息、文件历史快照、元数据仍可用于恢复、调试、分支与统计。
- **恢复可确定**：靠 UUID 链和 boundary 规则重建，而非依赖“按文件顺序猜测”
#### 五、为什么文件回退用 message UUID 关联，而不是简单按时间戳？
- **UUID 是逻辑会话节点身份**：可准确对应用户的某一次输入与该轮开始前的文件状态
- **工具调用可能并发**：工具结果通过 `sourceToolAssistantUUID` 绑定到具体 assistant tool-use，说明单靠时间顺序不足以稳定描述真实调用图
- **UUID 可跨恢复、分支和 JSONL 链重建保持引用关系**；时间戳只能表达“何时写入”，不能唯一表达“回退到哪一个对话决策点”