## 一、两套互补的记忆机制
- **CLAUDE.md** ：由用户手动写入，适合写入，项目规范、团队约定、构建命令、架构说明
- **Auto Memory 自动记忆**：由 Claude 自动写，写入内容可能为：你的纠正与偏好、积累的构建命令、调试心得

><mark style="background:rgba(3, 135, 102, 0.2)"> 两套机制都只是参考型上下文，若期望无条件拦截某个操作，应该使用 **PreToolUse hook**，而不是把规则写进 CLAUDE.md</mark>

## 二、CLAUDE.md 介绍

#### 2.1 哪些内容可以加入到 CLAUDE.md
- Claude 第二次犯同样的错误
- 一次 Code Review 发现了 Claude Code 本该知道的项目知识
- 一个新同事需要同样的背景才能上手
- 你又一次把上次输入过的同样纠正打进了对话
CLAUDE.md 的放置原则，只放「每次会话都该记住的事实」：构建命令、团队约定、项目布局、“总是做 X” 这类长期规则。多步骤流程，或者只与局部相关的内容，应移到 **skill** 或 **Rules路径范围规则** 中

#### 2.2 CLAUDE.md 路径、加载顺序、权限
##### 2.2.1 CLAUDE.md 不同路径的作用
- **企业级**：全组织所有人，路径 `/Library/Application Support/ClaudeCode/CLAUDE.md` ，我未使用过
- **用户级**：个人的所有项目，路径 `~/.claude/CLAUDE.md`。适合：个人代码风格偏好、个人工具快捷方式
- **项目级**：团队共享，路径：`projectRoot/./CLAUDE.md`。适合：项目架构、编码标准、通用工作流
- **本地级**：个人当前项目使用，路径：`./CLAUDE.local.md`。适合：个人偏好的项目测试数据
- **子目录级**：与部分代码相关的规则，路径：`src/`、`api/` 等子目录下的 `CLAUDE.md`。适合：某部分代码相关的规则
##### 2.2.2 CLAUDE.md 加载顺序
企业级 > 用户级 > 项目级 > 本地级 > 子目录级
也就是说：最先读、最宽泛 → 最后读、最具体。
这里有两个关键细节：
- **同一目录内**：`CLAUDE.local.md` 会拼在 `CLAUDE.md` **之后**读取，所以你的个人笔记是该层级最后被读到的
- **子目录的 CLAUDE.md 不在启动时加载**：它会在 Claude 真正读到该目录下的文件时才**按需**加载进来，所以出现得最晚
##### 2.2.3 规则冲突时，后加载的影响最大
- 冲突时，规则的影响力，则是反过来的，子目录级 > 本地级 这样的顺序
- claudeMdExcludes 可以避免 Claude 加载除企业级之外的 CLAUDE.md

#### 2.3 如何写好一个 CLAUDE.md
- **大小控制**：**200 行以内**。超长会消耗更多上下文并**降低遵守度**
- **指令要具体可验证**：好的示例：“使用 2 空格缩进” ；坏的示例：“格式化好代码”
- **用 Markdown 结构组织**：用标题和列表分组。有组织的章节，比密集段落更容易被遵循
- **避免冲突**：定期检查多个 CLAUDE.md 与 `.claude/rules/`，删掉过时或矛盾的指令
- **只存不可推导的信息**：多步流程、局部规则，移到 skill 或路径范围规则

#### 2.4 .claude/rules 使用注意
大项目可以把指令拆进 `.claude/rules/` 目录，每个文件对应一个主题。
```text

your-project/

├── .claude/
│ ├── CLAUDE.md # 主项目指令
│ └── rules/
	  ├── code-style.md # 代码风格
	  ├── testing.md # 测试约定
	  └── security.md # 安全要求

```
规则分两类：
- 无 `paths` 前置元数据的规则：**启动时加载，优先级与 `.claude/CLAUDE.md` 相同**。
- 带 `paths` 前置元数据的路径范围规则：**只在 Claude 处理匹配文件时加载**，这是“只加载相关规则、省上下文”最实用的机制。

## 三、Auto Memory（自动记忆）
#### 3.1 生成时机
Claude 会在工作过程中自行判断哪些内容值得记住，常见来源包括：
- 你的纠正，例如“错了，用 X 不要用 Y”
- 明确指令，例如“记住总是用 pnpm”
- 重复出现的模式，例如你多次纠正同一问题
- 关键项目信息，例如构建命令、架构决策、重要路径

#### 3.2 隐式记忆的四种类型分类
- **user**：用户的角色、目标、偏好、职责、知识背景，用来调整 Claude 的协作方式
- **feedback**：用户对 Claude 工作方式的反馈，包含“以后避免什么 / 继续做什么”，强调记录原因和使用方式
- **project**：关于当前项目的目标、计划、事故、bug、长期背景，但必须是不能从代码或 git 历史直接推导出来的信息
- **reference**：外部系统入口，比如 Linear、Slack、Grafana dashboard 等

#### 3.3 如何存储记忆，如何加载记忆
##### 3.3.1 存储位置与文件结构
存储位置在本地，所以，**同一仓库的所有 worktree 和子目录共享一个记忆目录**。如果不在 Git 仓库中，则使用项目根目录。
```text
~/.claude/projects/<project>/memory/

存储路径真实举例：/Users/haoyang/.claude/projects/-Users-haoyang-Documents----norman-wiki/memory
```
存储的文件目录结构：
```text
~/.claude/projects/<project>/memory/
├── MEMORY.md # 每个记忆文件的索引及摘要，每次会话加载前 200 行 / 25KB，先到为准
├── debugging.md # 详细主题笔记，按需读取
└── api-conventions.md
```
##### 3.3.2 加载记忆机制
- **每轮对话固定加载索引文件**：加载 `MEMORY.md` 的前 200 行或 25 KB 数据，**模型每轮能看到 Memory 的索引文件**
- **需要使用记忆时使用大模型找出最相关的五个记忆文件**：扫描 memory 目录下的 md 文件，排除 memory.md。读取每个文件的前三行 front matter，获取 file name、description、type，并组成 manifest。使用特定的提示词（You are selecting memories that will be useful to Claude Code as it processes a user's query）使用大模型判断与用户当前的 query 选择最多五个相关的记忆，返回这些文件的路径。
- **读取最相关的五个记忆文件全文**：读取相关的记忆文件，并将记忆文件的内容通过 `relevant_memories` 字段传给大模型
- **记忆加载特点异步，不阻塞**：召回是异步预取，不阻塞主循环。每个用户 turn 开始时，会异步获取记忆，主循环会在后续 post-tools 阶段检查 prefetch 获取的记忆是否已经完成，
	- 如果完成，就注入相关记忆 attachment
	- 如果没完成，就本轮先跳过，下一次 loop iteration 再看
	- 如果整个 turn 结束前都没完成，就不会强行等待
- **去重与避免重复注入**：系统会收集历史上已经 收集过的 memory 路径，避免重复选择；也会检查文件状态，如果模型已经通过 Read/Write/Edit 接触过某个 memory 文件，就不再通过 attachment 重复注入

**优点：全程做去重、限量、非阻塞**

#### 3.4 隐式记忆如何查看与开关
Claude code 中使用 在 `/memory` 里可以：
- 浏览 auto memory 文件夹、打开记忆文件夹
- 查看当前会话加载的所有 CLAUDE.md、CLAUDE.local.md、rules 文件
- 开关 auto memory

关闭隐式记忆方式：
- 在 `/memory` 中关闭
- 或在 settings.json 设置 `"autoMemoryEnabled": false`
- 或设置环境变量 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`

## 四、实用的排查错误手段
#### 4.1 假设 Claude 不遵守 CLAUDE.md
- 先用 `/memory` 确认文件被加载
- 把指令写得更具体
- 检查 CLAUDE.md、Auto Memory 中是否有冲突指令
#### 4.2 指令必须在某时刻执行
比如：每次提交前必须跑某个检查。
做法：写成 **hook**，按生命周期事件以 shell 命令强制执行，与 Claude 的判断无关
#### 4.3 CLAUDE.md 太大
超过 200 行会降低遵守度。
对策：
- 用 rules路径范围规则按需加载
- 直接精简
#### 4.4  `/compact` 后指令丢失
项目根 CLAUDE.md 会在压缩后从磁盘重读、重新注入。**但子目录 CLAUDE.md 不会自动重注入**，等下次读到该目录文件才重载。只在对话里说过的指令会丢，写进 CLAUDE.md 才能持久
#### 4.5 monorepo 串入别人的 CLAUDE.md
可以用 `claudeMdExcludes` 按路径 / glob 跳过，但注意：**企业级 Managed policy 不可被排除**。
