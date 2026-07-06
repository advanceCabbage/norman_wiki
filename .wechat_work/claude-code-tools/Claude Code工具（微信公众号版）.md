# Claude Code 的工具系统：模型会调用工具，背后其实有一套运行时

很多人第一次用 Claude Code，会把它理解成：

> Claude 读懂你的需求，然后调用 `Read`、`Edit`、`Bash` 这些工具完成任务。

这个理解没错，但只说到第一层。

真正有意思的是：Claude Code 不是简单把一堆函数丢给模型，而是在模型和本地环境之间，搭了一套完整的工具运行时。

这套运行时至少要解决六个问题：

- 工具怎么注册？
- 模型到底看到了什么？
- 工具执行结果怎么回到模型？
- 哪些工具可以并发，哪些必须排队？
- Hooks 怎么插入流程？
- Permission 怎么决定一次调用能不能执行？

如果只看一次次 `tool_use`，会觉得它像函数调用。

但如果把整套链路串起来看，它更像一个 Agent 操作系统里的“调度层 + 安全层 + 扩展层”。

这篇文章就把 Claude Code 的工具系统拆开讲清楚。

---

## 一、工具不是函数，而是结构化对象

Claude Code 里的每个工具，首先是一个结构化对象。

它不只包含“怎么执行”，还包含“怎么描述给模型看”“入参怎么校验”“权限怎么判断”“结果怎么转换”等信息。

一个工具大致可以拆成几组字段。

基础信息：

```text
name
description
inputSchema
prompt
```

执行与校验：

```text
call
validateInput
checkPermissions
```

调度与安全：

```text
isConcurrencySafe
isReadOnly
```

结果转换与界面展示：

```text
mapToolResultToToolResultBlockParam
renderToolUseMessage
renderToolResultMessage
```

里面最关键的是这几类：

- name：工具名，比如 Read、Edit、Bash
- inputSchema：工具入参 schema
- prompt：给模型看的工具说明
- call：真正执行工具逻辑
- checkPermissions：工具自己的权限检查
- isConcurrencySafe：判断这次调用能不能并发执行
- mapToolResultToToolResultBlockParam：把工具结果转成模型能接收的 tool_result

所以，一个工具并不只是“某个函数”。

它同时是：

- 给模型看的能力说明
- 给运行时用的执行入口
- 给安全系统用的权限单元
- 给 UI 用的展示单元
- 给调度器用的并发判断单元

这也是 Claude Code 工具系统复杂但强大的地方。

---

## 二、本轮可用工具，是动态生成的

Claude Code 并不是启动后就把所有工具无脑塞给模型。

工具会先进入一个注册中心，再根据当前环境筛选出“本轮真正可用”的工具池。

大致流程是：

```text
所有候选工具
  -> 环境 / feature flag 过滤
  -> 权限 deny rule 过滤
  -> isEnabled 过滤
  -> 合并 MCP 工具
  -> 去重
  -> 得到本轮 tools
```

这意味着同一个 Claude Code，在不同模式下，模型能看到的工具可能不一样。

例如：

- 当前是否处于 REPL 模式
- 是否启用了某些 feature flag
- 项目或用户 settings 是否禁用了某些工具
- 是否接入了 MCP 工具
- 当前权限模式是否允许某类操作

这些都会影响最终工具池。

所以，当我们说“Claude Code 有哪些工具”时，其实要分清两层：

- 候选工具：代码里注册过的工具
- 可用工具：本轮会暴露给模型的工具

真正影响模型行为的是后者。

---

## 三、发给模型的，不是本地函数

Claude Code 最终发给 Anthropic API 的 `tools`，是结构化 JSON 字段，而不是把本地代码或函数体发给模型。

一个工具转换后，大致长这样：

```ts
{
  name: tool.name,
  description:
    await tool.prompt(...),
  input_schema:
    tool.inputJSONSchema
    ?? zodToJsonSchema(
      tool.inputSchema
    ),
  strict?: true,
  eager_input_streaming?: true,
  cache_control?: ...
}
```

模型主要能看到三类信息：

- 工具叫什么：`name`
- 工具能做什么：`description`
- 工具参数怎么填：`input_schema`

而这些本地运行时字段，模型看不到：

- `call`
- `checkPermissions`
- `validateInput`
- `isConcurrencySafe`
- `isReadOnly`
- `renderToolUseMessage`
- `renderToolResultMessage`
- `mapToolResultToToolResultBlockParam`

也就是说，模型知道“我可以调用 `Read`，参数应该是什么样”。

但它不知道 `Read` 在本地具体怎么实现，也不能直接绕开运行时去访问文件。

这里有一个很重要的边界：

```text
Claude Code
  -> Anthropic API

tools：
  结构化 JSON 字段

Anthropic API
  / Claude 服务内部

会根据：
  tools
  工具配置
  system prompt

构造工具使用提示
```

客户端没有把工具定义拼成一大段字符串发出去。

但 Anthropic API 内部会把工具信息纳入模型可见的工具使用提示中。内部具体怎么组织，不属于客户端协议的一部分，也不应该依赖。

---

## 四、工具结果有两条去向

工具执行后，`call()` 会先返回工具自己的业务结果。

然后 Claude Code 会调用：

```ts
mapToolResultToToolResultBlockParam(
  result,
  toolUseID
)
```

把结果转换成 Anthropic 消息协议里的 `tool_result` block。

成功时大致是：

```json
{
  "type": "tool_result",
  "tool_use_id": "...",
  "content": "..."
}
```

失败时会多一个错误标记：

```json
{
  "type": "tool_result",
  "tool_use_id": "...",
  "content": "...",
  "is_error": true
}
```

这里容易混淆的一点是：工具结果有两条去向。

一条给模型继续推理：

```text
mapToolResultToToolResultBlockParam
```

另一条给终端或界面展示：

```text
renderToolResultMessage
```

给模型看的结果，要服务下一轮推理。

给用户看的结果，要服务阅读和操作。

这两个目标不同，所以 Claude Code 把它们拆开处理。

---

## 五、Claude Code 里有哪些工具类型？

如果按用途粗略分类，Claude Code 的工具可以分成几大类。

文件与搜索：

- `Read`
- `Edit`
- `Write`
- `Glob`
- `Grep`
- `NotebookEdit`

Shell：

- `Bash`
- `PowerShell`

Web：

- `WebFetch`
- `WebSearch`
- `WebBrowser`

Agent 与任务：

- `Agent`
- `TaskCreate`
- `TaskGet`
- `TaskUpdate`
- `TaskList`
- `TaskOutput`
- `TaskStop`
- `TodoWrite`

规划：

- `EnterPlanMode`
- `ExitPlanMode`
- `VerifyPlanExecution`

MCP：

- MCP 动态工具
- `ListMcpResources`
- `ReadMcpResource`
- `McpAuth`

技能与扩展：

- `Skill`
- `SearchExtraTools`
- `ExecuteExtraTool`
- `DiscoverSkills`

调度 / 自动化：

- `CronCreate`
- `CronDelete`
- `CronList`
- `Sleep`
- `Monitor`
- `RemoteTrigger`

工作区 / 团队：

- `EnterWorktree`
- `ExitWorktree`
- `TeamCreate`
- `TeamDelete`
- `SendMessage`

其他：

- `Config`
- `Artifact`
- `Brief`
- `Goal`
- `LocalMemoryRecall`
- `VaultHttpFetch`
- `PushNotification`
- `SendUserFile`
- `ReviewArtifact`
- `SyntheticOutput`

但要注意：这些只是工具类型。

实际能不能用，还要看 feature flag、环境变量、运行模式和权限配置。

---

## 六、工具不是都能并发执行

Claude Code 有工具并发逻辑。

但它不是看到多个工具调用就全部并发，而是会检查每个工具的：

```ts
isConcurrencySafe(input)
```

规则可以概括为：

```text
如果当前没有工具在执行：
  可以执行

如果当前已有工具在执行：
  只有当新工具是 concurrency-safe，
  且所有正在执行的工具也都是 concurrency-safe，
  新工具才可以并发执行

否则等待
```

典型并发安全工具包括：

- `Read`
- `Glob`
- `Grep`
- `WebFetch`
- `WebSearch`
- `Agent`
- `TaskGet`
- `TaskList`
- `SearchExtraTools`
- `CronList`
- `LSP`
- `Sleep`

典型非并发工具包括：

- `Edit`
- `Write`
- `NotebookEdit`
- `TodoWrite`
- `ExecuteExtraTool`
- `Skill`
- `REPL`
- `EnterWorktree`
- `ExitWorktree`
- `CronCreate`
- `CronDelete`
- `TeamCreate`
- `TeamDelete`
- `SendMessage`

`Bash` 比较特殊。

只有当它被判定为只读命令时，才算并发安全。

比如这一组调用：

```text
[Read, Read, Edit, Read]
```

实际执行不是三个 `Read` 全部一起跑。

而是：

```text
Read1 + Read2 并发
等 Read1 / Read2 完成
Edit 独占执行
Edit 完成后
Read3 执行
```

为什么 `Read3` 不直接跨过 `Edit` 先跑？

因为队列不能随便重排。

如果后面的读取跨过前面的修改，就可能读到错误时序下的文件状态。

所以并发不是为了“越快越好”，而是在正确性前提下尽量快。

---

## 七、Hooks：在关键生命周期插入自定义逻辑

Hooks 是 Claude Code 留给用户、插件、系统的扩展点。

它允许你在关键生命周期里插入逻辑，例如工具调用前检查、调用后审计、权限请求时自动审批等。

工具相关 Hooks 主要有：

- `PreToolUse`
- `PostToolUse`
- `PostToolUseFailure`
- `PermissionRequest`
- `PermissionDenied`

其他生命周期 Hooks 包括：

- `UserPromptSubmit`
- `SessionStart`
- `Stop`
- `SubagentStop`
- `PreCompact`
- `PostCompact`
- `Notification`

Hooks 可以来自多个地方：

- 用户 settings
- 项目 `.claude/settings.json`
- 本地 `.claude/settings.local.json`
- managed / policy settings
- 插件
- SDK 注册
- session / frontmatter 动态注册

一个典型配置大致长这样：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo hello",
            "if": "Bash(git *)",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

其中：

- `matcher` 用来匹配事件对象，比如工具名
- `if` 用类似权限规则的语法进一步过滤具体调用
- `timeout` 用来限制 hook 执行时间

可以把 Hooks 理解成 Claude Code 的“生命周期插件机制”。

---

## 八、Hook 不只有 command，还有 prompt、http、agent

最常见的 hook 类型是 `command`。

但 Claude Code 还支持几种更高级的 hook 类型：`prompt`、`http`、`agent`。

### 1. `type: "prompt"`

`prompt` 的作用是发起一个轻量 LLM 请求，让模型判断某个条件是否满足。

它会把 hook 输入 JSON 替换进 `$ARGUMENTS`，然后要求模型返回：

```json
{ "ok": true }
```

或者：

```json
{ "ok": false, "reason": "..." }
```

如果 `ok: false`，hook 可以阻塞当前流程。

这种方式适合：

- 规则不好写死
- 需要自然语言判断
- 不需要读文件或多步验证

比如：判断一条 `Bash` 命令是否只是安全的只读检查。

### 2. `type: "http"`

`http` 的作用是把 hook 输入 JSON 通过 HTTP POST 发给外部服务。

它适合接入：

- 企业策略服务
- 审计系统
- 权限审批系统
- 安全扫描服务

例如，把 `Edit` / `Write` 的权限请求交给公司内部策略服务判断。

一个重要细节是：`http` hook 支持 header 环境变量插值，但必须显式声明 `allowedEnvVars`。

这样可以避免项目配置偷读敏感环境变量。

### 3. `type: "agent"`

`agent` 会启动一个可用工具的多轮 LLM agent，去完成更复杂的验证。

它比 `prompt` 更重，但能力也更强。

这个 agent 可以读取文件、搜索代码、查看 transcript，最后用结构化结果返回：

```json
{ "ok": true }
```

或者：

```json
{ "ok": false, "reason": "..." }
```

典型场景是：在停止前检查用户要求的测试是否真的运行并通过。

三种类型简单对比：

```text
prompt：让 LLM 快速判断一个条件，轻量
http：交给外部服务判断或审计，适合企业策略
agent：让能用工具的子 agent 做复杂验证，最重但能力最强
```

---

## 九、Permission：真正决定工具能不能执行

Permission 是工具调用的安全闸门。

它回答的问题很直接：

```text
这次工具调用到底能不能执行？
```

Permission 会综合很多因素：

- deny rules
- ask rules
- allow rules
- 工具自己的 `checkPermissions`
- safety check
- permission mode
- bypassPermissions
- auto mode classifier
- 用户交互确认
- headless / async agent 限制

Hooks 和 Permission 很容易混在一起，但它们不是一回事。

可以这样区分：

```text
Hooks：
  外部可插拔逻辑
  可审计、阻断、补充上下文、改写输入

Permission：
  内建安全决策系统
  最终决定工具调用 allow / ask / deny
```

一个关键点是：

> Hook 的 allow，不等于彻底绕过 Permission。

比如 `PreToolUse` hook 返回 allow 后，仍然不能绕过 settings 里的 deny / ask rules，也不能绕过安全检查。

Permission 才是最终安全决策系统。

---

## 十、一次工具调用的完整链路

把上面的模块串起来，一次工具调用大致会经过这些步骤：

```text
1. 找到工具
2. 解析 inputSchema
3. validateInput
4. 执行 PreToolUse hooks
5. 解析 hook 产生的
   permission decision
   / updatedInput
6. 执行 Permission 判断
7. 如果拒绝，返回 is_error tool_result
8. 必要时执行 PermissionDenied hooks
9. 如果允许，执行 tool.call
10. 映射 tool_result
11. 执行 PostToolUse hooks
12. 如果工具执行异常，
    执行 PostToolUseFailure hooks
```

所以顺序不是“Permission 完全先于 Hooks”。

更准确地说是：

```text
PreToolUse hooks
  -> Permission
  -> tool.call
  -> PostToolUse
  -> PostToolUseFailure hooks
```

而 `PermissionRequest` hook 更像是在权限请求环节插入自动审批或拒绝逻辑。

这类机制尤其适合 headless、自动化、企业策略场景。

---

## 结语：Claude Code 的工具系统，本质是一套 Agent Runtime

Claude Code 的工具系统，可以压缩成一句话：

```text
工具以结构化 schema 暴露给模型，
以本地 runtime 执行，
以 Permission 控制安全，
以 Hooks 提供扩展，
以并发调度提升效率。
```

它不是简单的“函数调用列表”。

更准确地说，它是一套完整的 Agent Runtime：

- 工具定义负责告诉模型“能做什么”
- 工具执行负责真正“做”
- Permission 负责判断“能不能做”
- Hooks 负责在关键节点插入自定义逻辑
- 并发调度负责在正确性前提下提高效率

理解了这几层，再看 Claude Code 的一次次工具调用，就不会只看到表面的 `tool_use`。

你会看到背后的调度、安全、扩展和上下文管理体系。

这也是为什么 Claude Code 看起来像一个命令行工具，但它的内核更接近一个面向 Agent 的运行时系统。
