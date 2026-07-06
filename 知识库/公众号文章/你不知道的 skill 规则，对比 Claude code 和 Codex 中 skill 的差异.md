## 1. Claude code 中 skill 渐进式加载机制

Claude code 的三层渐进式加载机制

##### 第一层：首轮只加载摘要

SkillTool 的 prompt 只告诉模型：可用 skill 会在 system-reminder 里列出，需要时调用 Skill 工具。这一步只包含名称（name）和描述（descriptiont，不直接加载完整的 skill 内容。

##### 第二层：调用时加载完整内容

模型调用：

```json
{ "skill": "some-skill", "args": "..." }
```

此时才会将 SKILL.md 的正文内容全部加载，注入到消息对话，同时会处理：

```text
allowed-tools
arguments
model
effort
hooks
CLAUDE_SKILL_DIR
CLAUDE_SESSION_ID
```

#### 第三层：路径触发的动态 skill

有些 skill frontmatter 可以写 paths。这类 skill 初始不会进入可用列表，而是先放到 conditionalSkills 中。当模型执行 Read / Write / Edit 文件操作时，

1. 沿文件路径向上查找嵌套的 .claude/skills
2. 动态加载新发现的 skill 目录
3. 如果某个 conditional skill 的 paths 匹配当前文件，就激活它

举例：react-review skill 必须在 tsx 文件加载时才被激活，仅此最开始这个 skill 不会放到可用列表中，需要在后续分析 tsx 文件时才动态激活

```yaml
---
name: react-review
description: Review React components
paths: src/**/*.tsx
---
```

一句话总结，当前仓库的 skill 不是一次性把所有 SKILL.md 全塞进模型上下文，而是：

```text
扫描目录/插件/MCP/bundled
-> 解析 frontmatter 和描述
-> 作为 Command 注册
-> 用 skill_listing 给模型看轻量列表
-> 模型调用 Skill 后才注入完整 SKILL.md
-> 文件操作过程中再动态发现/激活更局部的 skill
```

## 2.在 Claude Code 中出现重名 skill 时的加载顺序

首先所有的 skill 被合并到数组中，调用 skill 时用 findCommand()函数，返回第一个 name 匹配到 skill，因此同名时谁排在数组前面，谁就会被调用。

合并 skill 目录的加载顺序是：全局.claude > user .claude > project .claude 。额外需要提及的是 skill 去重是按照物理文件路径去重，而不是按照 skill 名称去重。

假设用户级和项目级存在同名 skill，此时会命中用户级 skill

## 3. Description 长度限制与推荐长度

| 平台/标准             | 限制                                                                                                    |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Agent Skills 开放标准 | `description` 最大 1024 字符                                                                              |
| Claude Code       | `description + when_to_use` 在 skill listing 中默认最多 1536 字符；可通过 `skillListingMaxDescChars` 调整           |
| Codex             | 官方 Codex 文档未给出单个 `description` 字段上限；初始 skills 列表总预算最多为模型上下文窗口的 2%，未知窗口时为 8000 字符；超出时优先缩短 descriptions |

**推荐长度：**

- 为了跨平台兼容：**不超过 1024 字符**。
- 为了触发稳定和可读性：推荐 **200-500 字符**。
- 如果项目中 skills 很多：推荐 **150-350 字符**

**写法建议：**

1. 第一短句写核心能力。
2. 第二短句写触发场景。
3. 把关键词放在前半部分，因为长描述可能被截断。
4. 不要写实现细节；实现步骤放在 `SKILL.md` 正文。

推荐模板：

```yaml
description: Generate release notes from git history, PR summaries, and issue links. Use when the user asks to draft changelog, release notes, version summaries, or summarize changes for a release.
```

不推荐：

```yaml
description: Helps with releases.
```

## 4. Claude Code 支持的 Skill 元数据

Claude Code 的 `SKILL.md` frontmatter 支持以下字段：

| 字段 | 作用 |
| --- | --- |
| `name` | 展示名；多数布局下不决定 `/skill-name` 的命令名 |
| `description` | 描述 skill 做什么、什么时候用；用于自动触发判断 |
| `when_to_use` | 额外触发说明；会追加到 description 后 |
| `argument-hint` | 自动补全时显示参数提示 |
| `arguments` | 声明命名位置参数，用于 `$name` 替换 |
| `disable-model-invocation` | 禁止模型自动调用，只允许用户手动调用 |
| `user-invocable` | 是否在 `/` 菜单展示 |
| `allowed-tools` | skill 激活时免确认使用的工具 |
| `disallowed-tools` | skill 激活时移除的工具 |
| `model` | skill 激活时临时覆盖模型 |
| `effort` | skill 激活时临时覆盖 reasoning effort |
| `context` | `fork` 表示在隔离 subagent 上下文运行 |
| `agent` | `context: fork` 时指定 subagent 类型 |
| `hooks` | 绑定到 skill 生命周期的 hooks |
| `paths` | 限制哪些文件路径场景下可自动激活 |
| `shell` | skill 中动态命令使用的 shell |

### Claude Code 最佳示例

适合 Claude Code 专用 skill：

```md
---
name: review-pr
description: Review a pull request for correctness, test coverage, regressions, and maintainability. Use when the user asks to review a PR, inspect a branch, or identify risky changes before merge.
when_to_use: Trigger for requests mentioning PR review, merge readiness, regression risk, test gaps, or code review.
argument-hint: "[pr-number-or-branch]"
arguments:
- target
allowed-tools:
- Read
- Grep
- Bash(git diff *)
- Bash(gh pr view *)
effort: high
---
Review $target.
1. XXX
2. XXX
```

**注意：** 如果希望跨平台通用，不要把 `when_to_use`、`allowed-tools`、`effort` 等 Claude Code 专属字段写进通用 `SKILL.md`。

## 5. Codex 支持的 Skill 元数据

### `SKILL.md` 中的元数据

Codex 官方文档中，`SKILL.md` 必须包含：

| 字段 | 作用 |
| ------------- | ----------------------------------------------- |
| `name` | skill 名称 |
| `description` | 描述 skill 做什么、什么时候用；用于隐式调用判断 |

示例：

```md
---
name: commit
description: Stage and commit changes in semantic groups. Use when the user wants to commit, organize commits, or clean up a branch before pushing.
---
1. XX
2. XX
```

## 禁用 Skill简易记忆版

| 目的        | Claude Code                      | Codex                              |
| --------- | -------------------------------- | ---------------------------------- |
| 禁单个 skill | `skillOverrides: "off"`          | `enabled = false`                  |
| 只禁自动触发    | `disable-model-invocation: true` | `allow_implicit_invocation: false` |
| 禁全部 skill | `deny: ["Skill"]`                | 文中未写全局禁用方式                         |

## 6. Claude Code：如何禁用 Skill

### 完全禁用某个 Skill

在 Claude Code 中，完全禁用某个 skill 推荐使用 `skillOverrides`，在.claude/settings.json 中配置：

```json
{
	"skillOverrides": {
		"deploy": "off"
	}
}
```

**重点：**

- `/skills` 菜单操作会写入 `.claude/settings.local.json`。
- `skillOverrides: { "name": "off" }` 会让该 skill 对 Claude 隐藏，也不出现在 `/` 菜单。
- `skillOverrides` 不影响 plugin skills；plugin skills 需要通过 `/plugin` 管理。

### 只禁止自动触发，保留手动调用

在该 skill 的 `SKILL.md` frontmatter 中配置：

```yaml
---
name: deploy
description: Deploy the application to production.
disable-model-invocation: true
---
```

含义：

- Claude 不会根据用户请求自动调用该 skill。
- 用户仍然可以手动 `/deploy` 调用。

### 禁用所有 Skill 调用

在 Claude Code 权限 deny rules 中禁用 `Skill` 工具，在.claude/settings.json 中配置：

```json
{
	"permissions": {
		"deny": ["Skill"]
	}
}
```

语法说明：

- `Skill`：匹配所有 skill 调用。
- `Skill(name)`：精确匹配无参数调用，例如 `/deploy`。
- `Skill(name *)`：匹配带参数前缀，例如 `/deploy production`。
- deny 优先级高于 ask 和 allow；如果写了 `Skill` 作为 deny，不能再用 allow rule 给某个 skill 做例外。

## 7. Codex 禁用配置

完全禁用某个 skill，在 `~/.codex/config.toml` 中写：

```toml
[[skills.config]]
path = "/path/to/skill/SKILL.md"
enabled = false
```

改完后重启 Codex

只禁止隐式调用，保留显式 `$skill-name` 调用：

```yaml
policy:
allow_implicit_invocation: false
```

配置位置：

```text
my-skill/agents/openai.yaml
```

## 8. 选型建议

### 追求跨平台通用

只在 `SKILL.md` 写：

```yaml
---
name: my-skill
description: Clear description of what this skill does and when to use it.
---
```

把平台专属配置放到平台专属文件中。

### 只服务 Claude Code

可以使用 Claude Code 专属 frontmatter，例如：

```yaml
allowed-tools:
- Read
- Grep
effort: high
disable-model-invocation: true
```

### 只服务 Codex

保持 `SKILL.md` 简洁，把 UI、调用策略、依赖放到：

```text
agents/openai.yaml
```
