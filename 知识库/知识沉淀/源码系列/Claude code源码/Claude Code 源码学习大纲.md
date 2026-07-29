# Claude Code 源码学习大纲：一个面向软件工程的 Agent Runtime

> 本文只归纳本目录已有的源码分析笔记，不替代原笔记。学习 Claude Code 时，不应把它理解成“调用模型 + 几个工具”，而应把它看作：**以安全的工具执行、可恢复的会话和受控的上下文为基础，为软件工程任务优化的 Agent Runtime 与产品。**

## 一、先建立总心智模型

```text
用户 / IDE / CLI
        ↓
交互与模式（Plan、权限确认、Slash Command）
        ↓
主 Agent Query Loop
 ┌──────┼──────────────────────────────────┐
 ↓      ↓                  ↓               ↓
Prompt  Tool Runtime       Session          Context Governance
分层     执行/权限/Hooks    Transcript       检索/裁剪/压缩/恢复
        ↓                  ↓               ↓
   Subagent / Coordinator  文件历史     Memory / Skill
```

理解源码时，始终围绕四个问题阅读：模型在何时看到什么、模型能请求什么、请求何时真正执行、状态怎样持久化并在长任务中恢复。

## 二、模块地图

### 2.1 Agent 主循环：一次任务如何推进

对应笔记：[CC主循环Loop机制](CC主循环Loop机制.md)、[CC工具机制](CC工具机制.md)。

- 主循环负责“模型回复 → 工具调用 → 工具结果回灌 → 下一次模型请求”的闭环。
- 一次调用不是单纯的文本生成；工具结果会作为后续上下文，直到模型停止、用户取消或任务终止。
- Plan Mode 将“先对齐方案”显式产品化；它不等同于权限控制，后者仍在工具运行时决定。
- 工具可并发，但并发以正确性为先：只读、`concurrencySafe` 工具可以并发；`Edit`、`Write` 等写操作形成顺序屏障，不能让读取跨过尚未完成的写入。

**面试应说清的边界**：Loop 决定执行顺序和状态推进；模型并不直接拥有文件系统或 shell 权限。

### 2.2 Tool Runtime：把概率模型接到确定性世界

对应笔记：[CC工具机制](CC工具机制.md)、[CC agent如何修改代码](CC%20agent如何修改代码.md)、[CC 实现修改文件的 approve、reject及代码回退](CC%20实现修改文件的%20approve、reject及代码回退.md)。

- **工具协议**：模型只收到 `name`、面向模型的 `prompt/description` 和 `input_schema`；`call`、输入校验、权限检查、并发标记等本地运行时实现不会暴露给模型。
- **执行链**：模型提出调用 → 参数校验 → `checkPermissions` → `allow / ask / deny` → 真正 `call` → 将结果转换为 `tool_result` 并回灌模型。
- **双重描述**：面向模型的工具说明追求准确、参数与边界；面向用户的 UI 描述追求可读、风险透明和可审查。这是避免模型协议与人机交互互相妥协的设计。
- **安全边界**：Prompt 只能引导；Permission、Sandbox、Hook 与审批才是强制边界。`deny` 直接拒绝，受保护路径通常要求确认，`acceptEdits` 或 allow 规则才可自动通过。
- **编辑策略**：从全文件重写、行号 Diff，演进为 `old_string` 唯一匹配的字符串替换。它把模型不擅长的精确计数交给确定性逻辑，并要求编辑后重新读取，防止过期文件视图。
- **可回退性**：文件快照按会话消息 UUID 关联，而不是只按时间戳；这样可以稳定对应具体对话决策点和并发工具调用图。

**核心结论**：Claude Code 的安全与可靠性不是“模型足够听话”，而是“模型只表达意图，运行时验证并执行”。

### 2.3 Prompt、Skill 与 Memory：模型上下文如何按需构建

对应笔记：[Claude Code 提示词部分](Claude%20Code%20提示词部分.md)、[Skill 的秘密](Skill%20的秘密.md)、[CC 记忆机制](CC%20记忆机制.md)。

- **分层 Prompt**：稳定规则置于可缓存的系统前缀；环境、模式、记忆、MCP 状态等易变信息后置。目标是最大化 Prompt Cache 命中并减少注意力噪音。
- **工具不是 System Prompt 正文**：工具以结构化 schema 传递；工具文本、Skill 正文、对话消息属于不同上下文层。
- **Skill 是“能力目录 + 按需展开”**：先以 `skill_listing` 提供名称和描述；实际匹配任务时才由 `Skill` 工具加载完整 `SKILL.md`。已发送 Skill 会去重，压缩后优先恢复已调用的 Skill，而不是重塞全部候选。
- **路径与优先级**：Skill 可由路径动态发现；同名命令按统一 command 列表匹配。笔记记录的顺序为 `bundled > builtin plugin > managed > user > project`，设计 Skill 时必须防止同名遮蔽。
- **记忆检索**：常驻信息与可检索记忆分开；独立 selector 根据“用户问题 + 记忆索引”筛选少量相关文件，再向主 Agent 注入正文。selector 输出必须受 manifest 校验，不能让它凭空造路径。
- **Side Query 分工**：压缩、记忆筛选、记忆提取、权限解释、验证等各自使用更窄且可校验的 Prompt，避免一个巨型 Prompt 兼任所有工作。

#### 2.3.1 记忆系统的专题树

对应笔记：[CC 记忆机制](CC%20记忆机制.md)。这是最容易混淆的部分，建议分成“显式规则”和“自动长期记忆”两条线：

```text
记忆 / 指令系统
├─ 显式、确定性规则：CLAUDE.md 与 .claude/rules
│  ├─ 内容：项目约束、命令、架构边界、工作流
│  ├─ 路径与加载顺序：用户级、项目级、目录级规则
│  ├─ 冲突原则：后加载的规则影响更大
│  └─ 排障：文件过大、路径误命中、compact 后是否重注入
└─ 自动、选择性长期记忆：Auto Memory
   ├─ 生成：由独立流程抽取稳定事实、偏好、决策和待办
   ├─ 存储：记忆文件与 manifest/摘要
   ├─ 检索：selector 先选相关文件，主 Agent 再读正文
   └─ 控制：可查看、可关闭；不把所有历史自动塞给模型
```

这里的关键不是“记忆文件越多越好”，而是不同确定性等级的信息走不同路径：必须遵守的规则走 `CLAUDE.md`/rules 并在必要时重建；可能相关的历史事实走选择性检索；对话过程本身仍由 transcript 保存。

### 2.4 会话、Transcript 与文件历史：完整事实记录不等于模型上下文

对应笔记：[CC Session、Transcript、Resume机制](CC%20Session、Transcript、Resume机制.md)、[CC 记忆机制](CC%20记忆机制.md)。

- 用户消息、助手消息、工具调用和工具结果都会追加到 JSONL transcript；工具调用随对应 assistant message 落盘，工具结果随回填的 user message 落盘。
- `resume` 从 transcript 中按 `parentUuid` 重建最新有效链，并恢复会话附属状态，如文件历史、已读文件、标题、模式、worktree 等。
- `compact` 不删除旧 JSONL，而是追加 `compact_boundary` 和摘要；随后模型面向上下文按边界投影为“摘要 + 边界后有效消息 + 必要保留片段”。
- `clear` 创建新的 session，而不是抹除旧 transcript。
- UUID 是逻辑会话节点身份，可跨恢复、分支和并发工具调用引用；时间戳只能说明写入时间，无法可靠表达回退目标。

### 2.5 上下文治理：五层减负，最后才做全量摘要

对应笔记：[CC 上下文压缩机制](CC%20上下文压缩机制.md)。

1. **Tool result budget**：超大结果先落文件，仅向模型提供预览与文件路径；单条超过约 50K 字符、或同轮聚合超过约 200K 字符时触发。
2. **Snip**：用户或模型在规则触发时，将过远历史移出未来模型请求。
3. **Microcompact**：对可重新获取的旧工具观察做时间/缓存维度清理，避免缓存失效后继续携带高成本内容。
4. **Context Collapse（笔记中为 stub）**：设计上是读时投影，当前实现需要与实际版本区分，不能把设计注释当成功能事实。
5. **Auto-Compact**：接近窗口阈值时，用当前模型生成结构化摘要；`prompt_too_long` 时可 reactive compact 并重试一次。

压缩后，系统会重新注入最近读取文件、Plan、模式指令、已调用 Skill、未完成异步 Agent、MCP/Hook 状态等。**摘要负责提炼任务历史；不可丢失的运行时约束必须重建，不能托付给摘要。**

### 2.6 Multi-Agent：隔离、通信与并发，而不是“多开几个模型”

对应笔记：[CC 多Agent机制](CC%20多Agent机制.md)。

- **常规 Subagent**：父子型。子 Agent 的读文件状态复制，禁止任意写全局 UI 状态，仅保留后台任务登记通路；深度受限以避免递归失控。
- **工具隔离**：子 Agent 不可再派 Agent、不可抢用户问答权、不可切换 Plan Mode、不可停止其他任务；后台 Agent 进一步采用白名单。
- **通信**：父→子通过 `pendingMessages` 在工具调用边界取信；子→父把结果作为特殊消息回注入父 Agent 的上下文，复用主 Loop，而非另造等待状态机。
- **Fork Subagent**：从父 Agent 的完整上下文分叉，并尽力维持系统 Prompt、工具顺序、对话前缀一致，以命中 Prompt Cache，降低子任务启动成本与延迟。
- **Coordinator**：主从型，协调者只派 worker、收结果、综合结论；worker 执行调研、实现与验证。它适用于大型可并行工程任务，不应为简单问题增加协调成本。

### 2.7 代码检索、验证与日常工程实践

对应笔记：[CC代码检索机制](CC代码检索机制.md)、[CC面试题](CC面试题.md)、[Boris 自己平时怎么用 Claude Code？](Boris%20自己平时怎么用%20Claude%20Code？.md)。

- 代码检索应服务于“建立可编辑的当前文件视图”，而不只是找到关键字；大文件需要目录、范围读取与后续精读配合。
- **检索三件套**：`Glob` 先限定文件集合，`Grep` 找符号与调用点，`Read` 建立带行号的局部文件视图；三件套不足时再让只读 Explore 子 Agent 扩大搜索面，LSP 则补充语义级跳转与引用能力。这个顺序体现了“先便宜、确定的本地检索，再投入独立推理”的取舍。
- Verification Agent 与实现者分离，可减少同一上下文中的确认偏差。
- 工程最佳实践是：复杂任务先 Plan；用权限白名单而非跳过权限；用 `PostToolUse` 自动格式化；高频流程沉淀为 Skill/Slash Command；团队共享并持续维护 `CLAUDE.md`。

## 三、推荐学习顺序

1. 先读主循环、工具与编辑机制，建立“模型—运行时”边界。
2. 再读 Transcript、压缩与记忆，理解长任务为何不会只靠聊天记录。
3. 再读 Prompt、Skill、Tool Search，理解上下文与成本如何控制。
4. 最后读 Multi-Agent、检索、验证，把单 Agent Runtime 扩展到复杂工程协作。

## 四、30 秒面试总结

Claude Code 的核心不是一个会写代码的聊天机器人，而是一套面向软件工程的 Agent Runtime：模型通过结构化 Tool Schema 表达意图，运行时用 Permission、Sandbox 和 Hooks 强制执行边界；会话以可追溯 JSONL transcript 保存，模型上下文则通过检索、工具结果外置、snip 与 compact 动态投影；Skill 和记忆按需加载，多 Agent 通过字段级隔离与消息回注入实现并发协作。因此它的优势在于工程任务的安全性、可恢复性和长上下文治理，而代价是运行时机制、Prompt 与权限配置的复杂度更高。
