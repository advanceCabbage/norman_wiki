## 一、开篇定调
Claude code 的工具系统，本质上是一套 Agent Runtime。理解 Claude code 的工具执行机制，将会看到背后的调度、安全、扩展和上下文管理体系
```text

1. 工具以结构化 schema 暴露给模型，
2. 以本地 runtime 执行，
3. 以 Permission 控制安全，
4. 以 Hooks 提供扩展，
5. 以并发调度提升效率。

```

它不是简单的“函数调用列表”。更准确地说，它是一套完整的 Agent Runtime：
- 工具定义负责告诉模型“能做什么”
- 工具执行负责真正“做”
- Permission 负责判断“能不能做”
- Hooks 负责在关键节点插入自定义逻辑
- 并发调度负责在正确性前提下提高效率
## 二、 工具是结构化对象
工具不只包含“怎么执行”，还包含“怎么描述给模型看”“入参怎么校验”“权限怎么判断”“结果怎么转换”等信息。
一个工具大致可以拆成几组字段
###### 2.1 基础信息
- name：工具名，比如 Read、Edit、Bash
- **description：面向用户**，用一句人类可读的话说明“这一次具体要做什么”
- inputSchema： 工具入参 schema
- **prompt：面向大模型（发送时取该字段）**，说明工具能力、适用边界、使用规则、参数语义、示例和约束
###### 2.2 执行与校验
- call：真正执行工具逻辑
- validateInput
- checkPermissions：工具自己的权限检查
###### 2.3 调度与安全
- isConcurrencySafe ：判断工具能不能并发执行
- isReadOnly
###### 2.4 结果转换与界面展示
- mapToolResultBlockParam：把工具结果转成模型能接收的 tool_result
- renderToolUseMessage：在界面上显示“模型准备做什么”
- renderToolResultMessage：在界面上显示“工具执行出了什么结果”
## 三、模型接收到的工具结构
Claude Code 最终发给 Anthropic API 的 `tools`，是结构化 JSON 字段，而不是把本地代码或函数体发给模型。一个工具转换后，大致长这样：

```ts

{

	name: tool.name,
	description: await tool.prompt(...),
	input_schema: tool.inputJSONSchema ?? zodToJsonSchema(tool.inputSchema),
	strict?: true,
	eager_input_streaming?: true,
	cache_control?: ...
}

```
模型主要能看到三类信息：
- 工具叫什么：`name`
- 工具能做什么：`description`
- 工具参数怎么填：`input_schema
而这些本地运行时字段，模型看不到：
- `call`
- `checkPermissions`
- `validateInput`
- `isConcurrencySafe`
- `isReadOnly`
**优势**：
- 模型知道可以调用 XX 工具，但它并不知道 XX 工具的具体实现，也不能绕开运行时去访问文件
- 客户端没有把工具所有工具定义拼接为一大段字符串发送给大模型
## 四、Claude code 的工具类型
###### 4.1 文件与搜索
- `Read`
- `Edit`
- `Write`
- `Glob`
- `Grep`
###### 4.2 Shell
- Bash
-  PowerShell
###### 4.3 Web
- WebFetch
- WebSearch
###### 4.4 Agent 与任务
- Agent
- TaskCreate
- TodoWrite
- ...
###### 4.5 规划
- EnterPlanMode
- ExitPlanMode
###### 4.6 技能与扩展
- Skill
- SearchExtraTools
- ExecuteExtraTool
## 五、工具并发执行策略
Claude Code 有工具并发执行逻辑，但具备特定的并发执行策略，规则可以概括为：
- 如果当前没有工具在执行：可以执行工具
- 如果当前已有工具在执行，
	- 只有当新工具是 concurrencySafe 且所有正在执行的工具也都是concurrencySafe 为 true 新工具才可以并发执行
	- 否则新工具等待执行
**典型并发安全工具**包括：Read、Glob、WebFetch 、LSP、Sleep 等
**典型非并发工具**包括：Edit、Write、CronCreate、Skill
特殊工具 Bash，当 Bash 为仅读时，才算并发安全执行工具
真实举例：
```text
[Read, Read, Edit, Read]
```
实际执行不是三个 `Read` 全部一起跑，而是，Read 1 + Read 2 并发；等 Read 1 / Read 2 完成；Edit 独占执行；Edit 完成后；Read 3 执行。
**为什么队列不能随便重排。如果后面的读取跨过前面的修改，就可能读到错误时序下的文件状态。所以并发不是为了“越快越好”，而是在正确性前提下尽量快**
## 六、hooks 在工具生命周期
hooks 是 Claude Code 留给用户、插件、系统的扩展点。它允许你在关键生命周期里插入逻辑，例如**工具调用前检查、调用后审计、权限请求时自动审批**等。hooks 就是 Claude code 的生命周期插槽
###### 6.1 工具相关 hooks
- `PreToolUse`：工具执行前
- `PostToolUse`：工具执行后
- `PostToolUseFailure`：工具执行失败
- `PermissionRequest`：权限请求时
- `PermissionDenied`：权限被拒绝
###### 6.2 其他生命周期 hooks
- `UserPromptSubmit`
- `SessionStart`：会话开始
- `Stop`：会话结束
- `SubagentStop`：子 agent 停止运行
- `PreCompact` ： 会话压缩前
- `PostCompact`：会话压缩后
- `Notification`：通知
###### 6.3 hooks 的结构定义
```json
{

	"hooks": {
		"PreToolUse": [{
			"matcher": "Bash",
			"hooks": [
				{
				"type": "command",
				"command": "echo hello",
				"if": "Bash(git *)",
				"timeout": 30
				}
			]
		}]
	}
}
```
- `matcher` 用来匹配事件对象，比如工具名
- `if` 用类似权限规则的语法进一步过滤具体调用
- `timeout` 用来限制 hook 执行时间
## 七、探索 hook 的四大类型
Claude code 的 hook 包含**四大类型：command、prompt、http、agent**
###### 7.1 类型一：command 类型
工具执行的类型通常是 command 类型，可以用于执行 shell、脚本、函数等

###### 7.2 类型二：prompt 类型
**定义**： `prompt` 的作用是发起一个轻量 LLM 请求，让模型判断某个条件是否满足。
**适合场景**：
- 规则不好硬编码
- 需要自然语言判断
- 不需要读文件或多步验证
**举例**：判断一条 `Bash` 命令是否只是安全的只读检查

###### 7.3 类型三：http 类型
**定义**：`http` 的作用是把 hook 输入 JSON 通过 HTTP POST 发给外部服务。
**适合场景**：
-  企业策略服务
-  审计系统
-  权限审批系统
- 安全扫描服务
**举例**：把 `Edit` / `Write` 的权限请求交给公司内部策略服务判断
**一个重要细节是**：`http` hook 支持 header 环境变量插值，但必须显式声明 `allowedEnvVars`。这样可以避免项目配置偷读敏感环境变量
###### 7.4 类型三：agent 类型
**定义**：`agent` 会启动一个可用工具的多轮 LLM agent，去完成更复杂的验证。它比 `prompt` 更重，但能力也更强。这个 agent 可以读取文件、搜索代码、查看 transcript
**适合场景**：在停止前检查用户要求的测试是否真的运行并通过

###### 7.5 总结
- command：可以用于执行 shell、脚本、函数等
- prompt：让 LLM 快速判断一个条件，轻量
- http：交给外部服务判断或审计，适合企业策略
- agent：让能用工具的子 agent 做复杂验证，最重但能力最强
## 八、两种工具执行的权限卡控
有两种方案可以阻止工具执行，分别是：**hooks 和 Permission**
Hooks 和 Permission 很容易混在一起，但它们不是一回事，可以这样区分：
- hooks：**外部可插拔逻辑**；可审计、阻断、补充上下文、改写输入
- Permission：**内建安全决策系统**；最终决定工具调用 allow / ask / deny
一个关键点是：Hook 的 allow，不等于彻底绕过 Permission。
比如 `PreToolUse` hook 返回 allow 后，仍然不能绕过 settings 里的 deny / ask rules，也不能绕过安全检查。Permission 才是最终安全决策系统。

#### 8.1 Permissions 的自定义配置示例

```json
{
  "permissions": {
    "allow": ["Read", "Glob", "Grep", "Bash(npm install)"],
    "ask": ["Bash(npm publish:*)"],
    "deny": ["Bash(rm -rf *)"],
    "defaultMode": "default"
  }
}
```
规则格式是 `ToolName` 或 `ToolName(ruleContent)`；例如 `Bash(npm install)` 会解析为工具名 `Bash` 与规则内容 `npm install`
可配置来源包括：用户级：`~/.claude/settings.json` 等等

## 九、一次工具执行全流程
- 找到工具
- 解析 inputSchema 并校验validateInput（入参）
- 执行 PreToolUse hooks
- 解析 hook 产生的，permission decision / updatedInput
- 执行 Permission 判断
	- 如果拒绝，返回 is_error tool_result，必要时执行 PermissionDenied hooks
	- 如果允许，执行 tool.call，映射 tool_result
- 执行 PostToolUse hooks
- 如果工具执行异常，执行 PostToolUseFailure hooks

## 十、Claude code 工具注入机制（不是全量注入）

Claude Code **不会**按用户本轮自然语言意图，发送和本轮问题相关的工具。Tool Search 功能是默认打开的。但当 Tool Search 功能关闭时，Claude code 会向大模型发送全量工具的 schema。当 Tool Search 功能开启时，Claude code 会采用固定发送核心工具 + 其余工具延迟加载的策略，目的是减少工具上下文、同时保持 tools 数组稳定并提高 Prompt Cache 命中率。
固定核心工具包括：
- 文件与 Shell：Bash、Grep、Glob、Read 等
- Agent 与用户交互：Agent、AskUserQuestion
- 任务管理：`TaskCreate` 等
- 规划:`EnterPlanMode`等
- 网络：`WebFetch` 等
- 代码智能：LSP
- SKill：Skill 工具
- **工具发现：`SearchExtraTools`（搜索延迟工具并获取其定义）、`ExecuteExtraTool`（按名称和参数执行延迟工具）**
其余工具属于非核心工具，需要延迟加载，例如：MCP 工具（读取和列举 MCP 来源）、`TeamCreate` 等

#### 10.1 模型如何发现和加载非核心工具、以及如何利用 Prompt Cache 命中率
- 首先：固定核心工具是通过结构化方式每轮请求都发送给大模型，大模型知道固定核心工具如何使用
- 其次：非核心工具，仅发送了工具的名称列表，未发送工具的定义、参数等信息给大模型。告知大模型延迟工具和 MCP 工具不在当前 tool list，必须先调用 SearchExtraTools，再调用 ExecuteExtraTool 执行工具
- 然后：首次请求时，所有名称都是“新名称”，因此会注入完整延迟工具名称列表。后续请求中，如果工具池没变，不会重复注入。如果一个 MCP Server 在会话途中连接成功，新增了工具，则下一次模型请求会重新注入当前完整清单
- 最后：非核心工具列表变化后，依旧能复用大模型服务端的 Prompt Cache，原因是：Prompt Cache 的关键是请求前缀稳定，包括：System Prompt、工具 Schema 数组、早期稳定消息前缀。因为工具 Scheme 数组依旧是固定工具因此可以利用 Prompt Cache

#### 10.2 示例

```javascript
<system-reminder>
<available-deferred-tools>
CronCreate
TeamCreate
mcp__slack__send_message
...
</available-deferred-tools>
IMPORTANT: The tools listed above are deferred-loading — they are NOT in your tool list. To use them, you MUST first discover a tool via SearchExtraTools, then invoke it with ExecuteExtraTool.

SearchExtraTools and ExecuteExtraTool are core tools already in your tool list right now — call them directly, do NOT use Bash/Glob to find them.

Steps:
1. SearchExtraTools({"query": "select:<tool_name>"}) — discover the tool and its schema
2. ExecuteExtraTool({"tool_name": "<name>", "params": {...}}) — invoke it with correct parameters
</system-reminder>

```
其中 `<available-deferred-tools>` 内每行只有 非核心工具的**工具名称**，不包含完整 description、参数 schema 或 `searchHint`。因此它是轻量的，告诉模型“有 CronCreate”
不把 CronCreate 的完整 schema 塞入 API tools 数组
