# 拆解 Claude Code 源码：Skill 是如何被发现、按需加载与持久化的？

很多人会把 Skill 理解成一份 `SKILL.md` 文件。

但从 Claude Code 的源码实现看，Skill 更像一套完整的能力调度机制：先让模型知道“有哪些能力”，再按需加载具体指令；在文件路径变化时动态发现局部能力；并在会话压缩与恢复后，尽量保留真正生效过的指令。

这篇文章从源码视角，把这套机制拆开讲清楚。

## 一、先分清：Skill 和 Tool 的加载逻辑并不一样

Skill 与 Tool 最大的区别，在于它们进入模型上下文的方式不同。

- **Tool**：每轮模型请求都会携带当前可用工具的 schema，因此每轮对话都会重复发送。
- **Skill**：作为 `system-reminder` 文本注入对话上下文，而不是 schema 结构。Claude Code 通过 `skill_listing` 向模型发送 Skill 信息；已经发送过的 Skill 不会重复发送。

以 Tool 的 schema 为例：

```json
{
  "name": "Read",
  "description": "Reads a file from the local filesystem...",
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "The absolute path to the file to read"
      },
      "offset": {
        "type": "number",
        "description": "The line number to start reading from"
      }
    },
    "required": ["file_path"]
  }
}
```

### 1.1 为什么 `skill_listing` 不会每轮都发送？

因为 `skill_listing` 是文本上下文，不是结构化的 tools 字段。它发送过一次后，已经存在于 transcript 中；继续重复发送不仅浪费 token，也会破坏 prompt cache。

因此，Claude Code 会维护一个“已发送 Skill”集合：

```text
sentSkillNames: Map<agentId, Set<skillName>>
```

每次只补充此前没有发送过的新 Skill。如果没有新增 Skill，就不再发送 `skill_listing`。

### 1.2 模型怎么知道列表不是完整的 Skill 内容？

关键在于 `Skill` 工具的 prompt 会明确告诉模型：

```text
可用 Skill 会列在 system-reminder 中
如果某个 Skill 匹配用户任务，必须先调用 Skill 工具
如果看到 command-name 标签，说明该 Skill 已经被加载
```

所以模型不会把 `skill_listing` 当成完整 Skill 内容，而是将其理解为：

```text
skill_listing:
  只是索引

Skill 工具调用结果:
  才是完整指令
```

这正是渐进式加载能够成立的前提。

## 二、同名 Skill 怎么加载和匹配？

Claude Code 的 Skill 来源不只有用户级和项目级，还包括内置 bundled Skill、内置插件 Skill、管理员托管 Skill、额外目录 Skill、插件 Skill，以及旧版 commands 兼容项等。

加载时，系统会按**真实文件路径**去重。也就是说：路径不同但名称相同的 Skill，都会被加载。

加载完成后，它们会统一转换成 prompt command。真正调用时，系统不会临时再按“用户级 / 项目级”查找，而是在统一 command 列表中，按顺序匹配第一个 `name` 或 `alias` 命中的 command。

按照 command 的排列顺序，同名 Skill 的优先级是：

```text
bundled > builtin plugin > managed > user > project
```

因此，当用户级与项目级存在同名 Skill 时，最终会命中用户级 Skill。这是设计同名 Skill 时尤其需要注意的行为。

## 三、Skill 不只是 Markdown：它有自己的数据模型

在 Claude Code 中，Skill 会被转换成一种 `prompt command`。

一个 Skill 主要包含以下信息：

```text
name
description
when_to_use
allowed-tools
arguments
argument-hint
model
effort
hooks
paths
context
agent
skillRoot
getPromptForCommand()
```

其中最关键的字段包括：

```text
name:
  Skill 的唯一调用名称

description / when_to_use:
  用于告诉模型这个 Skill 什么时候适合使用

getPromptForCommand():
  真正加载完整 Skill 内容的函数

allowed-tools / model / effort / hooks:
  Skill 调用后对后续执行环境产生影响

paths:
  用于路径触发的条件 Skill
```

换句话说，**Skill 不是单纯的一段 Markdown，而是“Markdown 指令 + 元数据 + 运行时行为”的组合。**

## 四、渐进式加载：Skill 分三层进入上下文

Claude Code 的 Skill 渐进式加载可以分为三层。

### 4.1 第一层：先发送 Skill 摘要

第一层不会发送完整的 `SKILL.md`，而是发送轻量列表，也就是 `skill_listing`。

其中主要包含：Skill name、description、when_to_use。

### 4.2 第二层：调用时才发送完整 Skill 内容

当模型判断某个 Skill 适合当前任务时，会调用结构化工具：

```json
{
  "skill": "commit",
  "args": "..."
}
```

这时系统才会加载完整的 `SKILL.md`，并将它作为 meta user message 注入对话。完整内容通常会带上 Skill 根目录；这一层才是真正意义上的“加载 Skill”。

```text
Base directory for this skill: <skillDir>

<SKILL.md 正文>
```

### 4.3 第三层：由文件路径触发的动态 Skill

第三层发生在文件操作过程中。

当模型执行 Read、Write、Edit 等工具时，系统会根据被操作的文件路径向上查找更局部的 `.claude/skills`。例如：

```text
repo/
  .claude/skills/project-skill/SKILL.md
  packages/api/
    .claude/skills/api-skill/SKILL.md
    src/user.ts
```

启动时可能只加载项目根部的 Skill。当模型读取：

```text
packages/api/src/user.ts
```

系统会发现：

```text
packages/api/.claude/skills/api-skill/SKILL.md
```

然后把它加入动态 Skill 集合。

此外，Skill frontmatter 中还可以写 `paths`。带 `paths` 的 Skill 初始不会进入普通可用列表，而是等待文件路径匹配后再激活。

例如：

```yaml
paths:
  - "packages/api/**"
```

这类 Skill 只有在模型操作匹配路径的文件时，才会变成可用 Skill。

## 五、`scripts`、`references`、`assets` 会自动加载吗？

不会。

对于本地文件型 Skill，Claude Code 的通用加载逻辑只会自动读取：

```text
SKILL.md
```

它不会把下面这些目录递归塞进上下文：

```text
scripts/
references/
assets/
```

这些资源应当在 `SKILL.md` 中主动说明，例如：

```text
references/api.md:
  API 细节，需要查接口时读取

scripts/check.py:
  验证脚本，需要检查结果时运行

assets/template.docx:
  模板文件，需要生成文档时使用
```

系统会提供 Skill 根目录：

```text
Base directory for this skill: <skillDir>
```

同时也支持在正文中使用：

```text
${CLAUDE_SKILL_DIR}
```

这样模型可以在需要时，通过 Read、Grep、Bash 等工具按需读取或执行这些资源。

因此，如果你在自己的 Agent 中设计 Skill，最好要求 Skill 作者在 `SKILL.md` 中清楚声明：

- 有哪些附属文件；
- 每个文件的作用是什么；
- 什么时候应该读取；
- 什么时候应该运行。

否则，即使模型能够访问这些文件，也不一定知道它们存在。

## 六、frontmatter 元信息如何影响运行时？

`allowed-tools`、`arguments`、`model`、`effort`、`hooks` 都属于 Skill 的 frontmatter 元信息。

它们不会在扫描阶段立刻全部生效，而是在 Skill 被调用、完整内容被加载时才生效。

### 6.1 `allowed-tools`

`allowed-tools` 表示这个 Skill 运行时需要哪些工具权限。

Skill 被调用后，系统会把这些工具加入当前上下文的允许规则中，使后续执行可以使用这些工具。

### 6.2 `arguments`

`arguments` 用于参数替换。

例如，Skill 声明：

```yaml
arguments:
  - file
```

正文中可以写：

```text
Analyze $file
```

当模型调用：

```json
{
  "skill": "analyze",
  "args": "src/index.ts"
}
```

系统会把参数替换进完整 Skill 内容。

### 6.3 `model` 与 `effort`

`model` 表示这个 Skill 希望使用的模型。

Skill 调用后，系统会修改后续 main loop 使用的模型配置。

`effort` 表示推理强度或努力程度，它会影响后续模型调用的 thinking / reasoning 配置。

### 6.4 `hooks`

`hooks` 是 Skill 关联的自动化行为。

它不是在扫描 Skill 时注册，而是在 Skill 真正被调用时才注册。这样可以避免未使用的 Skill hooks 过早影响当前会话。

整个过程可以概括为：

```text
扫描 Skill:
  解析这些字段，但不一定立刻生效

调用 Skill:
  加载完整内容
  应用 allowed-tools
  应用 model / effort
  注册 hooks
  记录 invoked skill
```

## 七、会话压缩后：系统保留什么？

这是 Skill 机制中最容易被误解的一点。

Claude Code 并不保证会话压缩后，完整的 `skill_listing` 一定还在。也就是说，它不会因为 compact 就重新发送所有 Skill 的 name / description。

原因在于：

```text
完整 skill_listing 重发成本较高
很多 Skill 只是候选能力，不一定真的用过
模型仍然拥有 Skill 工具 schema
真正重要的是保留已经调用过的 Skill 指令
```

因此，Claude Code 重点保留的是**已经调用过的完整 Skill 内容**。

当 Skill 被调用时，系统会记录：`skillName`、`skillPath`、`content`、`invokedAt`、`agentId`。在 compact 后，系统会生成 `invoked_skills` attachment，把已调用 Skill 的内容重新注入上下文：

```text
The following skills were invoked in this session.
Continue to follow these guidelines:

### Skill: xxx
Path: xxx

<skill content>
```

同时，它还会进行预算控制：

- 单个 Skill 最多保留约 5000 token；
- 所有 invoked Skills 的总预算约 25000 token；
- 按最近调用时间排序；
- 预算不足时丢弃较旧的 Skill。

所以，压缩后的策略不是“保留所有 Skill 声明”，而是**保留已经真正生效的 Skill 指令**。

## 八、Resume 后，Skill 状态如何恢复？

Resume 后主要要解决两个问题：

```text
1. 进程内的 invokedSkills 状态丢了
2. 如果重新发送 skill_listing，会造成重复上下文
```

Claude Code 的处理方式有两步。

第一，从历史消息中的 `invoked_skills` attachment 恢复已调用 Skill 状态。这样后续再次 compact 时，系统仍然知道哪些 Skill 曾经被调用过。

第二，在 resume 时抑制下一次 `skill_listing` 注入。因为此前的 Skill 列表通常已经存在于 transcript 中，重复发送只会浪费 token，并破坏 prompt cache。

因此，resume 后的逻辑可以概括为：

- 恢复 invoked Skills；
- 不重复发送旧的 skill listing；
- 后续如果发现新增 Skill，再发送增量 skill_listing。

## 九、总结：实现一套真正可用的 Skill 机制

Claude Code 的 Skill 机制，本质是一套“能力索引 + 按需展开”的系统。

它不是把所有能力一次性塞进上下文，而是：

- 先让模型知道有哪些能力；
- 再让模型按需调用能力；
- 调用后才加载完整指令；
- 文件路径变化时动态发现更局部能力；
- 压缩后保留已使用能力；
- resume 后恢复已使用能力状态。

如果要为自己的 Agent 实现类似机制，关键不只是支持一个 `SKILL.md` 文件，还要实现：

- Skill 注册表；
- Skill 摘要列表；
- Skill 工具；
- 按需加载完整内容；
- 动态路径发现；
- 调用后权限 / 模型 / hooks 生效；
- compact 后 invoked Skills 保留；
- resume 后状态恢复。

这才是 Claude Code Skill 机制真正有价值的地方。
