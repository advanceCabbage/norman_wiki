# Claude Code 工具系统拆解：注册、并发、Hooks、Permission 与延迟加载

这篇文章基于当前代码实现整理，目标是把 Claude Code 里的「工具系统」讲清楚：工具如何注册、如何暴露给模型、如何执行、如何并发、Hooks 和 Permission 分别做什么，以及为什么会有延迟加载工具。

## 一、工具是如何注册的？

Claude Code 里的每个工具都是一个结构化对象。一个工具通常包含这些核心能力：

```ts
{
  (name,
    inputSchema,
    prompt,
    description,
    call,
    checkPermissions,
    validateInput,
    isConcurrencySafe,
    isReadOnly,
    mapToolResultToToolResultBlockParam,
    renderToolUseMessage,
    renderToolResultMessage);
}
```

其中最关键的是：

- `name`：工具名，例如 `Read`、`Edit`、`Bash`
- `inputSchema`：工具入参 schema
- `prompt()`：给大模型看的工具说明
- `call()`：真正执行工具逻辑
- `checkPermissions()`：工具自己的权限判断
- `isConcurrencySafe()`：是否允许并发执行
- `mapToolResultToToolResultBlockParam()`：把工具结果转换成模型能接收的 `tool_result`

工具不是散落使用的，而是统一汇集到工具注册中心。注册中心会根据 feature flag、环境变量、权限规则、REPL 模式、MCP 工具等，生成本轮真正可用的工具池。

也就是说：

```text
所有候选工具
  -> 环境/feature 过滤
  -> 权限 deny rule 过滤
  -> isEnabled 过滤
  -> 合并 MCP 工具
  -> 去重
  -> 得到本轮 tools
```

## 二、发送给 Anthropic API 时，tools 携带了哪些信息？

客户端最终发送给 Anthropic API 的 `tools` 是结构化字段，不是字符串。

每个工具会被转换成类似这样的结构：

```ts
{
  name: tool.name,
  description: await tool.prompt(...),
  input_schema: tool.inputJSONSchema ?? zodToJsonSchema(tool.inputSchema),
  strict?: true,
  eager_input_streaming?: true,
  defer_loading?: true,
  cache_control?: ...
}
```

真正会给 API 的主要信息是：

- `name`：工具名
- `description`：由工具的 `prompt()` 生成，也就是模型看到的工具说明
- `input_schema`：工具入参 JSON Schema
- `strict`：可选，要求更严格遵守 schema
- `eager_input_streaming`：可选，支持细粒度工具输入流式传输
- `defer_loading`：可选，表示工具延迟加载
- `cache_control`：可选，控制 prompt cache

不会发送给模型的字段包括：

- `call`
- `checkPermissions`
- `validateInput`
- `isConcurrencySafe`
- `isReadOnly`
- `renderToolUseMessage`
- `renderToolResultMessage`
- `mapToolResultToToolResultBlockParam`

这些都是本地运行时逻辑，模型看不到。

需要特别区分两层：

```text
Claude Code -> Anthropic API：
  tools 是结构化 JSON 字段

Anthropic API / Claude 服务内部：
  官方文档说明，会根据 tools、工具配置、用户 system prompt 构造特殊 tool-use system prompt
```

所以客户端没有把 tools 拼成字符串发出；但 Anthropic API 内部会把工具定义纳入模型可见的工具使用提示中。内部具体字符串模板不是客户端协议的一部分，也不应该依赖。

## 三、工具返回值协议是什么？

工具执行后，`call()` 会返回工具自己的业务结果。

然后 Claude Code 会调用：

```ts
mapToolResultToToolResultBlockParam(result, toolUseID);
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

失败时会带上：

```json
{
  "type": "tool_result",
  "tool_use_id": "...",
  "content": "...",
  "is_error": true
}
```

工具结果既要给模型继续推理，也可能给终端 UI 渲染。两者不是一回事：

- 给模型：`mapToolResultToToolResultBlockParam`
- 给用户界面：`renderToolResultMessage`

## 四、工具按类别有哪些？

可以大致分成这些类：

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

调度/自动化：

- `CronCreate`
- `CronDelete`
- `CronList`
- `Sleep`
- `Monitor`
- `RemoteTrigger`

工作区/团队：

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

实际是否启用，还要看 feature flag、环境变量和运行模式。

## 五、工具是否并发执行？

有并发逻辑。

执行器会判断每个工具的：

```ts
isConcurrencySafe(input);
```

规则是：

```text
如果当前没有工具在执行：
  可以执行

如果当前有工具在执行：
  只有当新工具是 concurrency-safe，
  且所有正在执行的工具也都是 concurrency-safe，
  新工具才可以并发执行

否则等待
```

典型并发安全工具：

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

典型非并发工具：

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

`Bash` 比较特殊：只有被判定为只读命令时，才并发安全。

例如：

```text
[Read, Read, Edit, Read]
```

执行顺序不是三个 Read 全部并发。

实际是：

```text
Read1 + Read2 并发
等 Read1 / Read2 完成
Edit 独占执行
Edit 完成后
Read3 执行
```

原因是队列不会让后面的 `Read3` 跨过前面的非并发安全工具 `Edit`。

## 六、Hooks 是什么？

Hooks 是用户、插件或系统在关键生命周期注入逻辑的机制。

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

Hooks 可以来自：

- 用户 settings
- 项目 `.claude/settings.json`
- 本地 `.claude/settings.local.json`
- managed / policy settings
- 插件
- SDK 注册
- session / frontmatter 动态注册

配置形态大致是：

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

`matcher` 用于匹配事件对象，例如工具名。`if` 使用类似权限规则的语法，可以进一步过滤具体调用。

## 七、Hook 的 type：prompt、http、agent 分别做什么？

除了最常见的 `command`，这个系统还支持三种更高级的 hook 类型。

### 1. `type: "prompt"`

作用：用一个轻量 LLM 请求判断条件是否满足。

它会把 hook 输入 JSON 替换进 `$ARGUMENTS`，然后要求模型返回：

```json
{ "ok": true }
```

或：

```json
{ "ok": false, "reason": "..." }
```

如果 `ok: false`，hook 会阻塞当前流程。

示例：检查 Bash 命令是否安全。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "prompt",
            "if": "Bash(*)",
            "prompt": "判断下面这个工具调用是否只是安全的只读检查。如果会删除文件、改 git 历史、上传密钥或执行未知远程脚本，返回 {\"ok\":false,\"reason\":\"...\"}。输入：$ARGUMENTS",
            "timeout": 20,
            "model": "claude-sonnet-4-6"
          }
        ]
      }
    ]
  }
}
```

适合场景：

- 规则不好写死
- 需要自然语言判断
- 不需要读文件或多步验证

### 2. `type: "http"`

作用：把 hook 输入 JSON 通过 HTTP POST 发给外部服务。

适合接入：

- 企业策略服务
- 审计系统
- 权限审批系统
- 安全扫描服务

示例：把 `Edit` / `Write` 的权限请求交给内部策略服务。

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "http",
            "url": "https://policy.example.com/claude-code/permission",
            "headers": {
              "Authorization": "Bearer $POLICY_TOKEN"
            },
            "allowedEnvVars": ["POLICY_TOKEN"],
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

服务可以返回：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "deny",
      "message": "不要直接修改生成文件。"
    }
  }
}
```

`http` hook 支持 header 环境变量插值，但必须显式声明 `allowedEnvVars`，避免项目配置偷读敏感环境变量。

### 3. `type: "agent"`

作用：启动一个可用工具的多轮 LLM agent 做复杂验证。

它比 `prompt` 更重，但能力更强。这个 agent 可以读取文件、搜索代码、查看 transcript，最后必须用结构化输出返回：

```json
{ "ok": true }
```

或：

```json
{ "ok": false, "reason": "..." }
```

示例：在停止前验证测试是否真的跑过并通过。

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "agent",
            "prompt": "检查本轮对话 transcript 和代码变更，确认用户要求的测试是否已经运行且通过。如果没有看到明确测试通过证据，返回 {\"ok\":false,\"reason\":\"没有看到测试通过证据\"}。Hook 输入：$ARGUMENTS",
            "timeout": 60,
            "model": "claude-sonnet-4-6"
          }
        ]
      }
    ]
  }
}
```

简单对比：

```text
prompt：让 LLM 快速判断一个条件，轻量
http：交给外部服务判断或审计，适合企业策略
agent：让一个能用工具的子 agent 做复杂验证，最重但能力最强
```

## 八、Permission 是什么？和 Hooks 有什么区别？

Permission 是工具调用的安全闸门。

它回答的问题是：

```text
这次工具调用到底能不能执行？
```

Permission 会综合：

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

Hooks 是扩展点，Permission 是安全策略核心。

区别可以这样理解：

```text
Hooks：
  外部可插拔逻辑
  可审计、阻断、补充上下文、改写输入

Permission：
  内建安全决策系统
  最终决定工具调用 allow / ask / deny
```

一个关键点是：Hook 的 allow 不等于彻底绕过 Permission。

例如 `PreToolUse` hook 返回 allow 后，仍然不能绕过 settings 中的 deny / ask rules，也不能绕过安全检查。

## 九、工具调用时 Hooks 和 Permission 的顺序

一次工具调用的大致流程是：

```text
1. 找到工具
2. 解析 inputSchema
3. validateInput
4. 执行 PreToolUse hooks
5. 解析 hook 产生的 permission decision / updatedInput
6. 执行 Permission 判断
7. 如果拒绝，返回 is_error tool_result
8. 必要时执行 PermissionDenied hooks
9. 如果允许，执行 tool.call
10. 映射 tool_result
11. 执行 PostToolUse hooks
12. 如果工具执行异常，执行 PostToolUseFailure hooks
```

所以顺序不是「Permission 完全先于 Hooks」，而是：

```text
PreToolUse hooks
  -> Permission
  -> tool.call
  -> PostToolUse / PostToolUseFailure hooks
```

`PermissionRequest` hook 则更像是在权限请求环节插入自动审批/拒绝逻辑，特别适合 headless 或企业策略场景。

## 十、哪些工具会延迟加载？

延迟加载由两个工具配合完成：

- `SearchExtraTools`
- `ExecuteExtraTool`

规则是：

```text
Core tools 永远直接加载
非 core tools 默认延迟加载
alwaysLoad: true 的工具不延迟
```

Core tools 包括常用基础工具，例如：

- `Read`
- `Edit`
- `Write`
- `Bash`
- `Glob`
- `Grep`
- `Agent`
- `WebFetch`
- `WebSearch`
- `Skill`
- `TodoWrite`
- `SearchExtraTools`
- `ExecuteExtraTool`

非 core 工具，例如部分 MCP 工具、cron、team、worktree、remote trigger 等，通常需要先搜索发现，再执行。

模型使用延迟工具的流程是：

```text
1. SearchExtraTools({"query": "select:CronCreate"})
2. ExecuteExtraTool({"tool_name": "CronCreate", "params": {...}})
```

延迟加载的优势：

- 减少初始 tools 数组体积
- 降低 token 占用
- 减少无关工具干扰
- MCP 工具很多时尤其有效
- 降低工具 schema 变化导致 prompt cache 失效的概率

## 结语

Claude Code 的工具系统可以概括成一句话：

```text
工具以结构化 schema 暴露给模型，以本地 runtime 执行，以 Permission 控制安全，以 Hooks 提供扩展，以并发调度提升效率，以延迟加载控制上下文成本。
```

它不是简单的“函数调用列表”，而是一套完整的 agent runtime 协议：

- 工具定义负责告诉模型“能做什么”
- 工具执行负责真正“做”
- Permission 负责“能不能做”
- Hooks 负责“在关键节点插入组织/用户自定义逻辑”
- 并发执行负责“怎么更快做”
- 延迟加载负责“不要一开始把所有工具都塞给模型”

理解这几层之后，再看 Claude Code 的工具行为，就不会只看到一次次 `tool_use`，而是能看到背后的调度、安全和上下文管理体系。
