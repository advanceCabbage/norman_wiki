# 🧠 Claude Code 记忆机制

> Claude Code 每次会话都从「空白上下文」开始，靠 **CLAUDE.md** 和 **Auto Memory** 两套机制跨会话传递知识。
>
> 这篇文章讲清楚四件事：它们怎么加载、不同层级写什么、冲突时谁优先，以及怎么写好一个 CLAUDE.md。

---

## 一、核心：两套互补的记忆机制

Claude Code 依靠 **CLAUDE.md** 和 **Auto Memory（自动记忆）** 实现记忆。

两者在**每次会话开始时都会被加载到上下文**。Claude 会把它们当作**参考上下文**，而不是强制配置。因此，指令越具体、越简洁，Claude 遵循得越一致。

### CLAUDE.md

- **谁来写**：你手动写
- **内容**：指令与规则
- **适合什么**：项目规范、团队约定、构建命令、架构说明

### Auto Memory

- **谁来写**：Claude 自动写
- **内容**：学到的经验与模式
- **适合什么**：从你的纠正和偏好中积累构建命令、调试心得

> **关键认知：都不是「硬性强制」**
>
> 两套机制都只是参考上下文。要无条件拦截某个操作，应该使用 **PreToolUse hook**，而不是把规则写进 CLAUDE.md。

---

## 二、CLAUDE.md：放在哪、写什么

CLAUDE.md 可以存在于多个位置，并按「从宽泛到具体」分层。不同位置的作用范围也不同。

### 企业级（Managed policy）

- **位置**：macOS：`/Library/Application Support/ClaudeCode/CLAUDE.md`
- **作用范围**：全组织所有人
- **写什么**：公司编码规范、安全/合规要求

### 用户级

- **位置**：`~/.claude/CLAUDE.md`
- **作用范围**：你的所有项目
- **写什么**：个人代码风格偏好、个人工具快捷方式

### 项目级

- **位置**：`./CLAUDE.md` 或 `./.claude/CLAUDE.md`
- **作用范围**：团队共享，随 Git 提交
- **写什么**：项目架构、编码标准、通用工作流

### 本地级

- **位置**：`./CLAUDE.local.md`，记得加 `.gitignore`
- **作用范围**：只有你、当前项目
- **写什么**：个人沙箱 URL、偏好的测试数据

### 子目录级

- **位置**：`src/`、`api/` 等子目录下的 `CLAUDE.md`
- **作用范围**：该子目录
- **写什么**：只与这部分代码相关的规则

### 什么时候该往 CLAUDE.md 里加内容？

- Claude **第二次**犯同一个错
- 一次 Code Review 发现了 Claude 本该知道的项目知识
- 你又一次把上次输入过的同样纠正打进了对话
- 一个新同事需要同样的背景才能上手

### 放置原则

只放「每次会话都该记住的事实」：

- 构建命令
- 团队约定
- 项目布局
- “总是做 X” 这类长期规则

多步骤流程，或者只与局部相关的内容，应移到 **skill** 或 **路径范围规则** 中，见第五节。

---

## 三、加载顺序：拼接，不是替换

这是最容易被教程讲混的地方，需要单独拆开。

### 1. 加载顺序：从宽泛到具体

Claude Code 启动时，会**从当前工作目录向上遍历到文件系统根目录**，沿途加载每一个 `CLAUDE.md` 和 `CLAUDE.local.md`。

整体读取顺序可以理解为：

```text
企业级 Managed policy
        ↓
用户级 ~/.claude
        ↓
项目根 ./CLAUDE.md
        ↓
本地 CLAUDE.local.md
        ↓
子目录 CLAUDE.md（按需加载）
```

也就是说：

```text
最先读、最宽泛  →  最后读、最具体
```

这里有两个关键细节：

- **同一目录内**：`CLAUDE.local.md` 会拼在 `CLAUDE.md` **之后**读取，所以你的个人笔记是该层级最后被读到的。
- **子目录的 CLAUDE.md 不在启动时加载**：它会在 Claude 真正读到该目录下的文件时才**按需**加载进来，所以出现得最晚。

> **官方原文**
>
> All discovered files are **concatenated into context rather than overriding each other.**
>
> 不冲突的规则会**全部同时生效**。只有直接矛盾时，才需要判断谁影响更大。

### 2. 冲突时谁优先：后读 = 影响力大

冲突时的赢家顺序，通常是加载顺序的反过来。

越具体、越靠近当前编辑位置，影响力越大：

```text
子目录
  ＞ CLAUDE.local.md
  ＞ 项目根
  ＞ 用户级
  ＞ 企业级
```

### 3. 具体例子：编辑 `src/api/foo.ts` 时三处缩进冲突

**用户级规则**

- **文件**：`~/.claude/CLAUDE.md`
- **规则**：2 空格
- **读取时机**：最先

**项目根规则**

- **文件**：`./CLAUDE.md`
- **规则**：4 空格
- **读取时机**：中间

**子目录规则**

- **文件**：`src/api/CLAUDE.md`
- **规则**：Tab
- **读取时机**：最后，按需加载

这种情况下，通常会用 **Tab**，因为子目录规则最具体、读得最晚。

> **提醒：这是「软偏好」，不是硬保证**
>
> 官方措辞很克制：两条规则矛盾时，Claude *may pick one arbitrarily*。
>
> 所以正确做法是**主动消除冲突**，而不是指望靠层级覆盖兜底。

### 4. 别把「企业级」想反了

很多教程说「企业级优先级最高」，这其实把三件事混在了一起：

**加载顺序**

- **谁最强**：企业级**最先**读
- **性质**：客观顺序

**文字冲突影响力**

- **谁最强**：**子目录 / 最具体**最强，企业级最弱
- **性质**：软偏好，不保证

**一定被加载（不可排除）**

- **谁最强**：**企业级**，`claudeMdExcludes` 对它无效
- **性质**：硬机制

**真正强制执行**

- **谁最强**：managed `settings.json` / hooks，而非 CLAUDE.md
- **性质**：硬机制

> **一句话**
>
> 企业级的「强」不在于冲突取胜，而在于**一定在场、不可被排除**。
>
> 组织要真正不可违抗的限制，应该用 managed settings（如 `permissions.deny`、`sandbox`）或 hooks，由客户端强制执行。这和 CLAUDE.md 的优先级无关。

---

## 四、如何写好一个 CLAUDE.md

### 1. 控制大小

目标 **200 行以内**。超长会消耗更多上下文并**降低遵守度**，因为它每次会话都会整篇加载。

### 2. 指令要具体可验证

好的写法：

- “使用 2 空格缩进”
- “提交前跑 `npm test`”

不推荐：

- “格式化好代码”
- “测试你的改动”

### 3. 用 Markdown 结构组织

用标题和列表分组。有组织的章节，比密集段落更容易被遵循。

### 4. 避免冲突

定期检查多个 CLAUDE.md 与 `.claude/rules/`，删掉过时或矛盾的指令。

### 5. 只存不可推导的信息

多步流程、局部规则，移到 skill 或路径范围规则。

### 快速起步

在项目根目录运行：

```text
/init
```

Claude 会分析代码库，自动生成一份起始 CLAUDE.md，里面通常包含构建命令、测试指令和发现的约定。

如果已经存在 CLAUDE.md，它会建议改进，而不是直接覆盖。

### 用 `@import` 拆分文件

可以用 `@path/to/file` 语法，把其他文件嵌进来，便于模块化。

```text
See @README for project overview and @package.json for npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

注意：

- 支持相对路径和绝对路径
- 相对路径相对**引用它的文件**解析
- 最多递归 **4 层**
- 代码块和行内代码里的 `@path` **不会**被导入
- 如果只是想提到路径，不想触发导入，用反引号包起来

> **导入不省上下文**
>
> `@import` 只是组织手段。被导入的文件启动时一样会整段加载进上下文。

### AGENTS.md 兼容

Claude 只读 `CLAUDE.md`，不读 `AGENTS.md`。

如果仓库已有 `AGENTS.md`，可以用 `@AGENTS.md` 导入，或者建软链让多个工具共用同一套指令。

```bash
ln -s AGENTS.md CLAUDE.md
```

Windows 建软链需要管理员或开发者模式，也可以改用 `@import`。

### 一个冷知识

给人看的备注可以用块级 HTML 注释：

```html
<!-- 这是给人看的备注 -->
```

这类注释会在注入上下文前被剥离，**不占 token**。

---

## 五、`.claude/rules/`：模块化与路径范围规则

大项目可以把指令拆进 `.claude/rules/` 目录，每个文件对应一个主题。

```text
your-project/
├── .claude/
│   ├── CLAUDE.md           # 主项目指令
│   └── rules/
│       ├── code-style.md   # 代码风格
│       ├── testing.md      # 测试约定
│       └── security.md     # 安全要求
```

规则分两类：

- 无 `paths` 前置元数据的规则：**启动时加载**，优先级与 `.claude/CLAUDE.md` 相同。
- 带 `paths` 前置元数据的路径范围规则：只在 Claude 处理匹配文件时加载，这是“只加载相关规则、省上下文”最实用的机制。

示例：

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API 开发规则
- 所有接口必须做输入校验
- 使用标准错误响应格式
```

用户级规则放在：

```text
~/.claude/rules/
```

它会对所有项目生效，并且**先于**项目规则加载。因此项目规则的影响力更高。

---

## 六、Auto Memory（自动记忆）

Auto Memory 让 Claude **无需你动手**就能跨会话积累知识，例如：

- 构建命令
- 调试心得
- 架构笔记
- 风格偏好
- 工作习惯

它**不是每次都存**，而是会判断“这条信息将来是否有用”再决定。

> **版本要求**
>
> 需要 **Claude Code v2.1.59+**，默认开启。可以用下面命令查看版本：
>
> ```bash
> claude --version
> ```

### 1. 什么时机生成？

Claude 会在工作过程中自行判断哪些内容值得记住，常见来源包括：

- 你的纠正，例如“错了，用 X 不要用 Y”
- 明确指令，例如“记住总是用 pnpm”
- 重复出现的模式，例如你多次纠正同一问题
- 关键项目信息，例如构建命令、架构决策、重要路径

当界面上出现：

```text
Writing memory
Recalled memory
```

就说明它正在读写记忆文件。

### 2. 存在哪？怎么加载？

存储位置：

```text
~/.claude/projects/<project>/memory/
```

其中 `<project>` 由 **Git 仓库**推导。

所以，**同一仓库的所有 worktree 和子目录共享一个记忆目录**。如果不在 Git 仓库中，则使用项目根目录。

几个特点：

- 它是**机器本地**的
- **不跨机器 / 云环境同步**
- 可以用 `autoMemoryDirectory` 在 settings.json 中改到自定义路径

目录结构与加载规则：

```text
~/.claude/projects/<project>/memory/
├── MEMORY.md          # 索引，每次会话加载前 200 行 / 25KB，先到为准
├── debugging.md       # 详细主题笔记，按需读取
└── api-conventions.md
```

> **加载差异**
>
> 启动时只加载 `MEMORY.md` 的前 200 行或 25KB，先到为准。
>
> 其他主题文件会在 Claude 需要时按需读取。
>
> 对比一下：**CLAUDE.md 无论多长都会整篇加载**，而 MEMORY.md 有 200 行 / 25KB 上限。


### 3. 隐式记忆（auto Memory）类型有哪些，如何加载的？

##### 3.1 隐式记忆包括四种类型
- **user**：用户的角色、目标、偏好、职责、知识背景，用来调整 Claude 的协作方式
- **feedback**：用户对 Claude 工作方式的反馈，包含“以后避免什么 / 继续做什么”，强调记录原因和适用方式。
- **project**：关于当前项目的目标、计划、事故、bug、长期背景，但必须是不能从代码或 git 历史直接推导出来的信息。
- **reference**：外部系统入口，比如 Linear、Slack、Grafana dashboard 等。
##### 3.2 隐式记忆文件内容格式
- MEMORY.md 文件中会存储所有记忆文件的索引信息
- XXX.md （具体记忆文件）会记录具体内容以及name、description、type 等
```
MEMORY.md

- [个人日记条目](diary_entry.md) — 记录个人日常想法和感受
```

```
diary_entry.md

---
name: 个人日记条目
description: 记录个人日常想法和感受
type: project
---

**2026-07-06**: 我爱喝牛奶
**Why:** 这是一个简单的个人日记条目，记录了当天的个人喜好。
**How to apply:** 这个记忆可以用于了解用户的个人偏好，在未来的对话中可以作为参考。
```
##### <font color="#ff0000">3.3 <font color="#ff0000">隐式记忆的加载逻辑</font></font>
- 加载 `MEMORY.md` 的前 200 行或 25KB 数据，模型每轮能看到 Memory 的索引文件
- 扫描 memory 目录下的 md 文件，排除 memory.md。读取每个文件的前三行 front matter，获取 file name、description、type，并组成 manifest。使用 特定的提示词（You are selecting memories that will be useful to Claude Code as it processes a user's query）使用大模型判断与用户当前的 query 选择最多五个相关的记忆，返回这些文件的路径。
- 读取相关的记忆文件，并将记忆文件的内容通过 `relevant_memories` 字段传给大模型
- 召回是异步预取，不阻塞主循环。每个用户 turn 开始时，会异步获取记忆，主循环会在后续 post-tools 阶段检查 prefetch 获取的记忆是否已经完成，
	- 如果完成，就注入相关记忆 attachment
	- 如果没完成，就本轮先跳过，下一次 loop iteration 再看
	- 如果整个 turn 结束前都没完成，就不会强行等待
- **去重与避免重复注入**：系统会收集历史上已经 surfaced 的 memory 路径，避免重复选择；也会检查 `readFileState`，如果模型已经通过 Read/Write/Edit 接触过某个 memory 文件，就不再通过 attachment 重复注入
- **优点：全程做去重、限量、非阻塞**
### 4. 如何查看 / 开关？

查看方式：

```text
/memory
```

在 `/memory` 里可以：

- 浏览 auto memory 文件夹
- 查看当前会话加载的所有 CLAUDE.md、CLAUDE.local.md、rules 文件
- 开关 auto memory
- 打开记忆文件夹

关闭方式：

- 在 `/memory` 中关闭
- 或在 settings.json 设置 `"autoMemoryEnabled": false`
- 或设置环境变量 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`

---

## 七、实用排错与冷知识

### Claude 不遵守 CLAUDE.md

原因：CLAUDE.md 以“系统提示词之后的用户消息”注入，**不保证严格遵守**。

对策：

- 先用 `/memory` 确认文件被加载
- 把指令写得更具体
- 检查是否有冲突指令

### 指令必须在某时刻执行

比如：每次提交前必须跑某个检查。

做法：写成 **hook**，按生命周期事件以 shell 命令强制执行，与 Claude 的判断无关。

### CLAUDE.md 太大

超过 200 行会降低遵守度。

对策：

- 用路径范围规则按需加载
- 或直接精简
- 注意：`@import` 拆分**不省**上下文

### `/compact` 后指令丢失

项目根 CLAUDE.md 会在压缩后从磁盘重读、重新注入。

但子目录 CLAUDE.md 不会自动重注入，等下次读到该目录文件才重载。

只在对话里说过的指令会丢，写进 CLAUDE.md 才能持久。

### monorepo 串入别人的 CLAUDE.md

可以用 `claudeMdExcludes` 按路径 / glob 跳过。

但注意：**企业级 Managed policy 不可被排除**。

---

## 八、一图速记

### CLAUDE.md

- **谁写**：你
- **加载量**：**整篇**加载
- **范围**：企业 / 用户 / 项目 / 本地 / 子目录
- **编辑方式**：直接改文件 / `/init` / `#` 快速记忆
- **强制力**：软，参考上下文，非强制

### Auto Memory

- **谁写**：Claude
- **加载量**：MEMORY.md 前 200 行 / 25KB
- **范围**：按仓库，worktree 共享，机器本地
- **编辑方式**：`/memory` 浏览编辑
- **强制力**：软

---

## 最后，用三句话记住

1. **加载**从宽泛到具体：企业 → 用户 → 项目 → 本地 → 子目录。它是**拼接，不是替换**。
2. **冲突**时反过来：越具体、越靠近你的规则越优先。但这是软偏好，不保证，最好别留下冲突。
3. **真正的强制**不靠 CLAUDE.md，而靠 **hooks / managed settings**。
