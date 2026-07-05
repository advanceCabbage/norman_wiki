

> [!abstract] 导读
> Claude Code 每次会话都从「空白上下文」开始，靠 **CLAUDE.md** 和 **Auto Memory** 两套机制跨会话传递知识。这篇讲清楚：它们怎么加载、不同层级写什么、冲突时谁优先、以及怎么写好一个 CLAUDE.md。

---

## 一、核心：两套互补的记忆机制

Claude Code 依靠 **CLAUDE.md** 和 **Auto Memory（自动记忆）** 实现记忆，两者在**每次会话开始时都会被加载到上下文**。Claude 把它们当作**参考上下文**，而非强制配置——指令越具体、越简洁，Claude 遵循得越一致。

| 机制              | 谁来写        | 内容       | 适合什么                  |
| --------------- | ---------- | -------- | --------------------- |
| **CLAUDE.md**   | 你手动写       | 指令与规则    | 项目规范、团队约定、构建命令、架构     |
| **Auto Memory** | Claude 自动写 | 学到的经验与模式 | 从你的纠正和偏好中积累的构建命令、调试心得 |

> [!warning] 关键认知：都不是「硬性强制」
> 两套机制都只是**参考上下文**。要无条件拦截某个操作，得用 **PreToolUse hook**，而不是写进 CLAUDE.md。

---

## 二、CLAUDE.md：放在哪、写什么

CLAUDE.md 可以存在于多个位置，**按「从宽泛到具体」分层**，作用范围各不相同：

| 层级                      | 位置                                                        | 作用范围           | 写什么               |
| ----------------------- | --------------------------------------------------------- | -------------- | ----------------- |
| **企业级（Managed policy）** | macOS：`/Library/Application Support/ClaudeCode/CLAUDE.md` | 全组织所有人         | 公司编码规范、安全/合规要求    |
| **用户级**                 | `~/.claude/CLAUDE.md`                                     | 你的所有项目         | 个人代码风格偏好、个人工具快捷方式 |
| **项目级**                 | `./CLAUDE.md` 或 `./.claude/CLAUDE.md`                     | 团队共享（随 Git 提交） | 项目架构、编码标准、通用工作流   |
| **本地级**                 | `./CLAUDE.local.md`（记得加 `.gitignore`）                     | 只有你、当前项目       | 个人沙箱 URL、偏好的测试数据  |
| **子目录级**                | `src/`、`api/` 等子目录下的 `CLAUDE.md`                          | 该子目录           | 只与这部分代码相关的规则      |

> [!question] 什么时候该往 CLAUDE.md 里加内容？
> - Claude **第二次**犯同一个错
> - 一次 Code Review 发现了 Claude 本该知道的项目知识
> - 你又一次把上次输入过的同样纠正打进了对话
> - 一个新同事需要同样的背景才能上手

> [!tip] 放置原则
> 只放「每次会话都该记住的事实」：构建命令、约定、项目布局、"总是做 X" 的规则。多步骤流程或只与局部相关的内容，应移到 **skill** 或 **路径范围规则**（见第五节）。

---

## 三、加载顺序：拼接，不是替换 ⭐

> [!info]
> 这是最容易被各类教程讲混的地方，单独拆开讲清楚。

### 加载顺序：从宽泛到具体

Claude Code 启动时**从当前工作目录向上遍历到文件系统根目录**，沿途加载每一个 `CLAUDE.md` 和 `CLAUDE.local.md`。整体读取顺序是：

```mermaid
flowchart LR
    A["🏢 企业级<br/>Managed policy"] --> B["👤 用户级<br/>~/.claude"] --> C["📁 项目根<br/>./CLAUDE.md"] --> D["🔒 本地<br/>CLAUDE.local.md"] --> E["📂 子目录<br/>按需加载"]
```

`最先读 · 最宽泛`  ───────────────►  `最后读 · 最具体`

两个关键细节：

- **同一目录内**：`CLAUDE.local.md` 拼在 `CLAUDE.md` **之后**读，所以你的个人笔记是该层级最后被读到的。
- **子目录的 CLAUDE.md 不在启动时加载**：它在 Claude 真正读到该目录下的文件时才**按需**加载进来（所以出现得最晚）。

> [!quote] 官方原文
> All discovered files are **concatenated into context rather than overriding each other.**
>
> 不冲突的规则**全部同时生效**，只有直接矛盾时才需要分胜负。

### 冲突时谁优先：后读 = 影响力大

冲突时的赢家顺序，**恰好是加载顺序的反过来**——越具体、越靠近你的，影响力越大：

> [!important] 冲突影响力排序
> **子目录 ＞ CLAUDE.local.md ＞ 项目根 ＞ 用户级 ＞ 企业级**
> （最具体、最靠近你的那个，赢）

> [!example] 具体例子：编辑 `src/api/foo.ts` 时三处缩进冲突
> | 文件 | 规则 | 读取时机 |
> | ---- | ---- | ------- |
> | `~/.claude/CLAUDE.md`（用户） | 2 空格 | 最先 |
> | `./CLAUDE.md`（项目根） | 4 空格 | 中间 |
> | `src/api/CLAUDE.md`（子目录） | Tab | 最后（按需） |
>
> → 通常用 **Tab**，因为子目录的规则最具体、读得最晚。

> [!warning] 这是「软偏好」，不是硬保证
> 官方措辞很克制：两条规则矛盾时 *"Claude may pick one arbitrarily"*。所以正确做法是**主动消除冲突**，而不是指望靠层级覆盖兜底。

### 别把「企业级」想反了：三条轴要分清

很多教程写「企业级优先级最高」，这其实把三件不同的事混为一谈了：

| 维度 | 谁最强 | 性质 |
| ---- | ------ | ---- |
| **加载顺序** | 企业级**最先**读 | 客观顺序 |
| **文字冲突影响力** | **子目录/最具体**最强，企业级最弱 | 软偏好，不保证 |
| **一定被加载（不可排除）** | **企业级**（`claudeMdExcludes` 对它无效） | 硬机制 |
| **真正强制执行** | managed `settings.json` / hooks（**非 CLAUDE.md**） | 硬机制 |

> [!key] 一句话
> 企业级的「强」不在「冲突取胜」，而在「**一定在场、不可被排除**」。组织要真正不可违抗的限制，得用 managed settings（`permissions.deny`、`sandbox`）或 hooks，由客户端强制执行，与 CLAUDE.md 的优先级无关。

---

## 四、如何写好一个 CLAUDE.md

| 原则 | 说明 |
| ---- | ---- |
| **控制大小** | 目标 **200 行以内**。超长会消耗更多上下文并**降低遵守度**；它每次会话整篇加载。 |
| **指令要具体可验证** | ✅"使用 2 空格缩进" / ❌"格式化好代码"；✅"提交前跑 `npm test`" / ❌"测试你的改动"。 |
| **用 Markdown 结构组织** | 用标题和列表分组，有组织的章节比密集段落更易被遵循。 |
| **避免冲突** | 定期检查多个 CLAUDE.md 与 `.claude/rules/`，删掉过时或矛盾的指令。 |
| **只存"不可推导"的信息** | 多步流程 / 局部规则移到 skill 或路径范围规则。 |

> [!tip] 快速起步
> 在项目根目录运行 `/init`，Claude 会分析代码库自动生成一份起始 CLAUDE.md（含构建命令、测试指令、发现的约定）。已存在时它会建议改进而非覆盖。

**`@import` 拆分文件**：用 `@path/to/file` 语法把其他文件嵌进来，便于模块化。

```text
See @README for project overview and @package.json for npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

- 支持相对/绝对路径，相对路径相对**引用它的文件**解析；最多递归 **4 层**。
- 代码块（``` ``` ```）和行内代码（`` ` ``）里的 `@path` **不会**被导入——想只提路径不导入，用反引号包起来。

> [!warning] 导入不省上下文
> `@import` 只是**组织手段**：被导入的文件启动时一样会整段加载进上下文。

**`AGENTS.md` 兼容**：Claude 只读 `CLAUDE.md`，不读 `AGENTS.md`。若仓库已有 `AGENTS.md`，用 `@AGENTS.md` 导入或建软链让两个工具共用同一套指令。

```bash
ln -s AGENTS.md CLAUDE.md   # 软链方式（Windows 建软链需管理员/开发者模式，改用 @import）
```

> [!tip] 冷知识
> 给人看的备注用 `<!-- 块级 HTML 注释 -->`，会在注入上下文前被剥离，**不占 token**。

---

## 五、`.claude/rules/`：模块化与路径范围规则

大项目可把指令拆进 `.claude/rules/` 目录，每个文件一个主题：

```text
your-project/
├── .claude/
│   ├── CLAUDE.md           # 主项目指令
│   └── rules/
│       ├── code-style.md   # 代码风格
│       ├── testing.md      # 测试约定
│       └── security.md     # 安全要求
```

- 无 `paths` 前置元数据的规则，**启动时加载**，优先级与 `.claude/CLAUDE.md` 相同。
- 带 `paths` 前置元数据的**路径范围规则**，只在 Claude 处理匹配文件时才加载——这是「只加载相关规则、省上下文」最实用的机制。

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API 开发规则
- 所有接口必须做输入校验
- 使用标准错误响应格式
```

> [!info]
> 用户级规则放 `~/.claude/rules/`，对所有项目生效，**先于**项目规则加载（即项目规则优先级更高）。

---

## 六、Auto Memory（自动记忆）

Auto Memory 让 Claude **无需你动手**就能跨会话积累知识：构建命令、调试心得、架构笔记、风格偏好、工作习惯。它**不是每次都存**，而是判断「这条信息将来是否有用」再决定。

> [!info] 版本要求
> 需 **Claude Code v2.1.59+**，默认开启。用 `claude --version` 查看版本。

### 1）什么时机生成？

Claude 在工作过程中**自行判断**哪些值得记住，常见来源：

- 你的纠正（"错了，用 X 不要用 Y"）
- 明确指令（"记住总是用 pnpm"）
- 重复出现的模式（你多次纠正同一问题）
- 关键项目信息（构建命令、架构决策、重要路径）

> [!note]
> 界面上出现 "Writing memory" / "Recalled memory" 时，就是它在读写记忆文件。

### 2）存在哪？怎么加载？

存储位置：**`~/.claude/projects/<project>/memory/`**

- `<project>` 由 **Git 仓库**推导，所以**同一仓库的所有 worktree 和子目录共享一个记忆目录**；不在 Git 仓库时用项目根目录。
- 它是**机器本地**的，**不跨机器/云环境同步**。
- 可用 `autoMemoryDirectory`（settings.json）改到自定义路径。

目录结构与加载规则：

```text
~/.claude/projects/<project>/memory/
├── MEMORY.md          # 索引，每次会话加载（前 200 行 / 25KB，先到为准）
├── debugging.md       # 详细主题笔记，按需读取
└── api-conventions.md
```

> [!important] 加载差异（易混点）
> - 启动时**只加载 `MEMORY.md` 的前 200 行或 25KB**（先到为准）；其余主题文件 Claude 需要时才按需读。
> - 对比：**CLAUDE.md 无论多长都整篇加载**，而 MEMORY.md 有 200 行 / 25KB 上限。

### 3）如何查看 / 开关？

- **查看**：会话中运行 `/memory`，选 auto memory 文件夹浏览。全是纯 Markdown，可读、可改、可删。
- **关闭**：`/memory` 里有开关；或在 settings.json 设 `"autoMemoryEnabled": false`；或环境变量 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`。

> [!info]
> `/memory` 命令会列出当前会话加载的所有 CLAUDE.md、CLAUDE.local.md、rules 文件，并能开关 auto memory、打开记忆文件夹。

---

## 七、实用排错与冷知识

| 现象 | 原因 / 对策 |
| ---- | ---------- |
| **Claude 不遵守 CLAUDE.md** | CLAUDE.md 以「系统提示词之后的用户消息」注入，**不保证严格遵守**。先用 `/memory` 确认文件被加载；把指令写得更具体；检查是否有冲突指令。 |
| **指令必须在某时刻执行**（如每次提交前） | 写成 **hook**，按生命周期事件以 shell 命令强制执行，与 Claude 的判断无关。 |
| **CLAUDE.md 太大** | 超 200 行降低遵守度。用路径范围规则按需加载，或精简。（`@import` 拆分**不省**上下文。） |
| **`/compact` 后指令丢失** | **项目根 CLAUDE.md 会在压缩后从磁盘重读、重新注入**；**子目录 CLAUDE.md 不会自动重注入**，等下次读到该目录文件才重载。只在对话里说过的指令会丢——写进 CLAUDE.md 才能持久。 |
| **monorepo 串入别人的 CLAUDE.md** | 用 `claudeMdExcludes`（settings）按路径/glob 跳过。但**企业级 Managed policy 不可被排除**。 |

---

## 八、一图速记

| 维度  | CLAUDE.md                  | Auto Memory              |
| --- | -------------------------- | ------------------------ |
| 谁写  | 你                          | Claude                   |
| 加载量 | **整篇**加载                   | MEMORY.md 前 200 行 / 25KB |
| 范围  | 企业 / 用户 / 项目 / 本地 / 子目录    | 按仓库（worktree 共享，机器本地）    |
| 编辑  | 直接改文件 / `/init` / `#` 快速记忆 | `/memory` 浏览编辑           |
| 强制力 | 软（参考上下文，非强制）               | 软                        |


> [!summary] 三句话总结
> 1. **加载**从宽泛到具体（企业→用户→项目→本地→子目录），是**拼接不是替换**；
> 2. **冲突**时反过来，**越具体越靠近你的越优先**（软偏好，不保证，最好别留冲突）；
> 3. **真正的强制**不靠 CLAUDE.md，靠 **hooks / managed settings**。



