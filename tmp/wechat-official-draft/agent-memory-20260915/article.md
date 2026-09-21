## 一、四层记忆机制

- <span style="display:inline;color:#35b378;font-weight:bold;">感知记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：当前输入的原始内容</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">短期记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：context window 里的对话历史，包括存入到 JSONL 中的文件</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">长期记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：存在外部数据库、语义检索召回 + 关键字检索</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">实体记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：已知历史对话提取的关键事实，比如：用户偏好习惯等。通常使用结构化存储</span>

实际设计时要解决三个核心问题：**存什么、怎么存、什么时候取出来用**。

## 二、OpenClaw 的记忆机制

### 2.1 记忆文件类型

- <span style="display:inline;color:#35b378;font-weight:bold;">用户身份信息类文件</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：AGENTS.md、`SOUL.md`、`IDENTITY.md`、`USER.md` 等文件，</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">长期记忆类</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：分两种类型，一类是可以跨任务、每次对话时均可见的内容存储在 MEMORY.md；另一类是明细层，支持按照日期、项目等主题创建的文件，存储在 memory 目录 `memory/YYYY-MM-DD.md`。判断一条记忆是写入 MEMORY.md 还是 memory 目录下是由 `AGENTS.md` 中的 Agent 行为约定，以及自己的提示词决定的</span>
### 2.2 记忆文件注入时机与注入策略

- <span style="display:inline;color:#35b378;font-weight:bold;">用户身份信息类文件</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：会在 session 首次执行时生成快照，session 运行途中修改身份信息文件，身份信息文件不会动态注入。通常需要重启 gateway、/new 或 /reset (new 是新建窗口；reset 是清空历史对话通常会保留模型选择)</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">长期记忆类</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：</span>
    - MEMORY.md 不超过 2 万字符时会全量注入到上下文中
    - 当模型判断当前用户问题中涉及旧决策、人物、偏好等时才主动调用记忆检索工具对 memory 文件夹中长期记忆进行混合检索，存储时使用的 SQLite 数据库既进行了向量存储也进行了原文存储，**混合检索时向量权重 0.7、全文 FTS 权重 0.3**。记忆检索时会阻塞主 agent，直到检索内容回来才会继续主 agent Loop

## 三、Claude Code 的记忆机制

### 3.1 记忆文件类型

- <span style="display:inline;color:#35b378;font-weight:bold;">显式记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：由人工或初始化生成的 CLAUDE.md 文件</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">隐式记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：由 Claude 自行总结的记忆文件，通常以 project 命名文件夹，存在四种类型的记忆文件，分别是：</span>
    - <span style="display:inline;color:#35b378;font-weight:bold;">user</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：用户的角色、目标、偏好、职责、知识背景，用来调整 Claude 的协作方式</span>
    - <span style="display:inline;color:#35b378;font-weight:bold;">feedback</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：用户对 Claude 工作方式的反馈，包含“以后避免什么 / 继续做什么”，强调记录原因和使用方式</span>
    - <span style="display:inline;color:#35b378;font-weight:bold;">project</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：关于当前项目的目标、计划、事故、bug、长期背景，但必须是不能从代码或 git 历史直接推导出来的信息</span>
    - <span style="display:inline;color:#35b378;font-weight:bold;">reference</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：外部系统入口，比如 Linear、Slack、Grafana dashboard 等</span>
### 3.2 记忆文件注入时机与注入策略

- <span style="display:inline;color:#35b378;font-weight:bold;">显式记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">： CLAUDE.md 文件会在会话开始从磁盘读取，注入到上下文中。使用 /clear、/compact 等均会再次从磁盘读取 CLAUDE.md 文件</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">隐式记忆</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：每轮对话都会加载 `MEMORY.md` 文件的前 200 行或 25 K 数据注入到上下文中，`MEMORY.md` 中存储的是隐式记忆文件的概要信息。主 agent 可以知道记忆信息的概要情况。</span>
    - 另外启动独立的记忆选择器，传入用户问题和各个记忆文件的 manifest，有单独的模型判断最相关的五个记忆文件，并以结构化 JSON 返回最多五个候选文件名。不阻塞主 agent 执行任务，主 agent 在每轮工具调用结束后检查记忆文件是否筛选完成，如果任务结束前都没有返回最相关的记忆文件则放弃

## 四、什么时候取记忆文件

- <span style="display:inline;color:#35b378;font-weight:bold;">主动检索</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：每次任务开始前，用当前任务的描述去检索相关记忆</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">被动触发</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：在 Agent 推理过程中，判断当前步骤需要某类特定知识时，主动发起检索。通过将「查记忆」封装成一个 Tool</span>

实践中将两种方式搭配使用。

## 五、社区开源的记忆存储库

### 5.1 Mem0

Mem0 的核心是把对话转化为可检索、可维护的长期记忆：写入时通过 LLM 提取用户偏好、背景等事实，结合已有记忆去重，再生成 embedding 并持久化。

Mem0 特别适合「个性化记忆」场景，检索时按 user_id 等限定范围，召回与当前问题相关的记忆，由应用注入模型上下文，实现跨会话个性化。

它的关键在于事实提取和记忆管理。

默认使用的 Qdrant 向量数据库，没有引入图数据库（Neo4j 等），使用普通数据库维护**实体 ->  关系 -> 实体**

### 5.2 Letta 莱塔

Letta 前身是大名鼎鼎的 MemGPT，Letta 把 Agent 的记忆分成了三个层级。
- <span style="display:inline;color:#35b378;font-weight:bold;">Core Memory</span><span style="display:inline;color:#3f3f3f;font-weight:normal;"> 是始终留在 context window 的核心信息，例如：用户画像</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">Recall Memory</span><span style="display:inline;color:#3f3f3f;font-weight:normal;"> 是最近的对话历史，类似于缓存，按时间顺序存储，支持快速回溯</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">Archival Memory</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：长期归档的知识</span>

最有意思的是，Letta 让 Agent 自己通过工具调用来管理记忆，Agent 决定在三个层级中移动记忆，例如将某条记忆从 Core Memory -> Recall Memory

### 5.3 Zep

Zep 引入了「时间感知」的概念，Zep 给每条记忆标注「有效时间窗口」。通过时序知识图谱来管理记忆的生命周期，自动识别过期记忆。

## 六、生产级记忆整合策略

**目的**：消除内容重复、内容过期、互相矛盾的记忆内容，提升检索的质量

### 6.1 去重

把语义相近的多条记忆合并成一条更完整的版本

### 6.2 冲突消解

当两条记忆互相矛盾时，保留时间更新最近的那条，另外一条标记为过期

### 6.3 抽象提炼

本质上是把情节记忆转化为语义记忆的过程
