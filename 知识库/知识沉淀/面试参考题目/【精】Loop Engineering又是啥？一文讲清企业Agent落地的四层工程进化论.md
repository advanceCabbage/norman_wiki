文章链接：[腾讯好文](https://mp.weixin.qq.com/s/3Zbx4RHB4fOdomI5aA_wIQ)
## 一、四层工程关系
- Context Engineering **包含** Prompt Engineering
- Harness Engineering **包含** Context Engineering
- Loop Engineering **包含** 以上所有

**首先**通过Prompt Engineering 和 Context Engineering 快速验证当前Case是否能通过AI解决，**其次**通过Harness Engineering 保证AI执行任务的成功率，**最后**通过Loop Engineering 提升AI执行任务的效率。

不要着急去实现Loop Engineering，在没有稳定的Harness Engineering的情况下，只会将问题放大到系统级别，2026年大部分人应该做的是Harness Engineering

## 二、四层工程分别对应哪些技术

- **Prompt Engineering** ： 
	- 角色设定（"你是一位资深财务分析师"）
	- 输出格式约束（"以 JSON 格式返回"）
	- Few-shot 示例（给 2-3 个输入输出样本）
	- Chain-of-Thought 引导（"让我们一步步思考"）
	- 结构化 prompt 模板（使用 XML/Markdown 分区）
- **Context Engineering**：
	- Prompt Engineering 
	- **RAG（检索增强生成）**：不把整个知识库塞给模型，而是根据用户查询，语义检索最相关的文档片段，只把这些片段放入 context。企业场景中，这意味着 Agent 可以回答关于内部流程、产品手册、合同条款的问题，而不需要对模型做微调
	- **MCP（Model Context Protocol）& Skill** ：Anthropic 主导的协议标准，让 Agent 通过统一接口连接外部数据源和工具。企业的 CRM、ERP、项目管理工具都可以通过 MCP 接入，Agent 在推理时实时拉取最新数据。
	- **Message History 管理** ：长对话中，早期消息的价值递减。Context engineering 通过滑窗（只保留最近 N 轮）、摘要压缩（把 20 轮对话压缩成 3 段摘要）、优先级排序（关键决策记录保留，闲聊丢弃）来维持 context 质量
	- **Tool Schema 精简**： 每个 tool definition 都占 context 空间。如果你给 Agent 接了 50 个工具，光是工具定义就吃掉了几千 token。Context engineering 要求只暴露当前任务需要的工具子集
- **Harness Engineering**：
	- **Guides（引导）：** AGENTS.md 或 CLAUDE.md 文件，编码了项目的规则、约定、禁忌。不同于 prompt 里的"请遵守编码规范"（概率性遵守），AGENTS.md 的每一行都对应一个曾经的失败模式——它是错误经验的结构化沉淀
	- **Sensors（感知）：** Output parser 验证输出格式、eval pipeline 评估输出质量、drift detector 检测 Agent 行为是否偏离预期。这些不是 Agent 自己的能力，而是 harness 提供的外部检查机制
	- **Enforcement（执行约束）：** Linter 在 Agent 生成不合规代码时阻止提交，test gate 在测试不通过时阻止合并，permission 系统限制 Agent 能访问的资源和能执行的操作。**确定性约束替代概率性遵守**——这是 L3 与 L2 的本质区别
	- **Context Pipeline（数据管线）：** 这就是 L2 的 context engineering，但在 L3 中它被 harness 的其他组件治理——什么时候加载什么 context，由 harness 的编排逻辑控制，而不是静态配置
	- **Observability（可观测性）：** 记录每个 turn 的完整 trace——input、output、tool calls、token count、latency、决策原因。对合规要求高的行业（金融、医疗、法律），这不是可选项而是硬性前提
-  **Loop Engineering** ：
	- **Automations（自动化心跳）** ：这是让 Loop 成为 Loop 而不是"你执行了一次"的关键。定时触发（每天早上）或事件触发（CI 失败时）自动运行 Agent 进行发现和分类。Codex 有 Automations tab，Claude Code 有 `/loop`、`/goal`、hooks、GitHub Actions
	- **Worktrees（工作树隔离）**： 多个 Agent 同时在同一个 repo 上工作时，如果不做隔离，文件冲突会让一切崩溃。Git worktree 为每个 Agent 创建独立的工作目录和分支，共享仓库历史但互不干扰编辑
	- **Skills（技能编码）**： 把项目的约定、构建步骤、"我们不这么做因为那次事故"写成可复用的 SKILL.md 文件。Agent 每次运行时读取 skill，而不是从零猜测你的项目习惯。这消除了"意图负债"（Intent Debt）——Agent 冷启动时会用自信的猜测填补你没说的部分，skill 把这些猜测替换为确定的规则
	- **Plugins / Connectors（插件/连接器）** ：基于 MCP 协议，让 Agent 能读 issue tracker、查数据库、调 staging API、发 Slack 消息。没有 connector 的 Loop 只能看文件系统——有了 connector 的 Loop 能在你的真实工作环境中行动
	- **Sub-agents（子 Agent）**： 最关键的结构模式：**写的人和查的人分开**。生成代码的 Agent 不给自己打分——另一个 Agent（不同指令，可能不同模型）做 review。这种 maker-checker 分离是 Loop 能在你不在场时运行的信任基础
	- **State（外部状态）** ：Markdown 文件、Linear board、或任何存活在 context window 之外的持久化存储。记录什么做完了、什么在进行、什么是下一步。Agent 在 session 间会忘记一切，但 repo 不会——state 文件是 Loop 跨 run 连续性的唯一保障
## 三、企业采纳路线
#### 阶段 1：夯实 L1 + L2

**目标：验证 "AI 能不能做这件事"。**

选择 2-3 个高频、低风险的业务场景（客服问答、文档生成、代码补全），做好 prompt 模板 + RAG pipeline + context 管理。

具体动作：

- 为每个场景建立结构化的 prompt 模板，包含角色设定、输出格式、边界约束
    
- 搭建 RAG pipeline 接入内部知识库，验证检索准确率
    
- 接入 MCP 连接 1-2 个业务系统（如 CRM、工单系统）
    
- 建立基础的 eval 流程——对比 Agent 输出与人工标准答案，计算准确率
    

**退出标准：** Agent 在选定场景上的准确率达到 85%+，且团队对 prompt + context 的优化已经进入收益递减阶段（改来改去提升不大了）。这时候你的瓶颈已经不在 L1/L2 了。

#### 阶段 2：建设 L3

**目标：让 Agent 能被信任独立完成任务。**

在验证过的场景上加 harness——从最简单的开始：

具体动作：

- 创建 AGENTS.md，把阶段 1 中发现的所有 Agent 失败模式编码为规则
    
- 在 CI pipeline 中接入 output validation（格式检查、业务规则检查）
    
- 对关键场景加 test gate——Agent 的输出必须通过自动化测试才能应用
    
- 搭建 observability pipeline——至少做到每次 Agent 执行的完整 trace 可查
    
- 建立 AGENTS.md 的持续更新机制：每次新的失败模式 → 分析根因 → 加规则
    

**退出标准：** Agent 在选定场景上可以半自主执行——人只需要做最终 review 而不是逐步监控。AGENTS.md 的增长速度放缓（说明常见失败模式已被覆盖）。

![Image](https://mmbiz.qpic.cn/sz_mmbiz_png/ZRhjO8xAWr6sq0dAST2UnXSsQABCv0JydicKRcHwoGVLPs7iaNql2d1pV4Fm55uhIRt08z7BewqaQWOXxo5O119gthmchxmk98ibfmuDNiaU2jM/640?wx_fmt=png&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=7)

#### 阶段 3：试点 L4

**目标：验证无人值守运行的可行性和 ROI。**

在 L3 最成熟的场景上试点 Loop——从最简单的 automation 开始。

具体动作：

- 选一个低风险、高频次的重复性任务（如每日 CI failure triage、代码风格修正、测试补全）
    
- 设计一个最小 Loop：automation（定时触发）+ 一个 builder sub-agent + 一个 reviewer sub-agent + state 文件
    
- 设置严格的 token budget 上限——每次 Loop run 不超过 X token
    
- 前两周保持高频人工 review（每次 Loop 输出都看），确认 Loop 行为符合预期
    
- 逐步降低 review 频率：每天 → 每两天 → 每周抽查
    
- 监控 comprehension debt：定期做 code walkthrough，确保团队仍然理解 Loop 生成的代码
    

**退出标准：** Loop 在试点场景上稳定运行 4 周+，人工 review 的否决率低于 10%，token 成本在预算范围内。此时可以考虑扩展 Loop 到更多场景。

#### 关键 Anti-Pattern：跳过 L3 直接搞 L4

这是最常见也最危险的错误。一些团队看到"Boris Cherny 一天合并 30 个 PR"的故事，就想直接跳到 Loop Engineering。但他们忽略了一个关键前提：Cherny 是在 Anthropic 内部、使用自家模型、有完善的 harness 基础设施的情况下做到这一点的。

  
没有 L3 的 L4 意味着：你搭了一个自动运行的系统，但这个系统里的每个 Agent 都是不可靠的。它不会停下来等你修复——它会持续产出需要人工善后的结果。你以为自动化节省了时间，实际上人工善后的成本可能超过了手动执行的成本。净效率不是正的，是负的