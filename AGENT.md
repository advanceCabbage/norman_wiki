# AGENT

> 这是知识库内容放置规则。Codex 和 Claude 在新增或整理文件时，都应优先遵循这里的目录约定。

## 目录树

> 更新于 2026-08-07。新增/移动文件后请同步此处。

```text
norman_wiki
├── AGENT.md
├── AGENTS.md
├── CLAUDE.md -> AGENT.md
├── 图片/                      # Obsidian 附件目录
└── 知识库
    ├── .claude
    │   └── skills
    │       └── citadel        # 学城（km.sankuai.com）操作 Skill
    │           ├── references
    │           │   ├── cli-reference.md
    │           │   ├── doc-insert.md
    │           │   ├── doc-update.md
    │           │   └── doc-view.md
    │           └── SKILL.md
    ├── AI资讯
    │   ├── AI早报.md
    │   ├── AI生图.md
    │   ├── README.md
    │   └── 产品发现.md
    ├── skills
    │   └── github-weekly-top10
    │       ├── scripts
    │       │   └── fetch_github_weekly_top10.py
    │       └── SKILL.md
    ├── 优秀的github
    │   └── 优秀的github仓.md
    ├── 公众号文章
    │   ├── Claude Code 不用 RAG，如何完成代码检索？（微信公众号版）-手绘封面.png
    │   ├── Claude Code 不用 RAG，如何完成代码检索？（微信公众号版）.md
    │   ├── Claude Code工具.md
    │   ├── Claude Code工具（微信公众号版）.md
    │   ├── Loop 机制详解：什么时候该让 AI 自己循环干活.md
    │   ├── 从 CC 源码获取到 Skill 的秘密（微信公众号版）.md
    │   ├── 你不知道的 skill 规则，对比 Claude code 和 Codex 中 skill 的差异.md
    │   ├── 如何写好Skill-手绘封面.png
    │   ├── 如何写好Skill：从触发词到信息层级的实战指南.md
    │   ├── 循环（Loops）什么时候该用.md
    │   ├── 🧠 Claude Code 记忆机制.md
    │   └── 🧠 Claude Code 记忆机制（微信公众号版）.md
    ├── 复习日记
    │   └── 整体计划.md
    ├── 小林大模型视频学习总结
    │   ├── 01-第一周 Agent-skill.md
    │   ├── 02-Claude code提示词.md
    │   ├── 02-第二周 Claude Code核心架构与实现原理.md
    │   ├── 03-第三周 openclaw.md
    │   ├── 北美找AI工作.md
    │   └── 岗位介绍  &  简历.md
    ├── 待买课程
    │   ├── AI电子伴侣企业级项目实战.md
    │   ├── 冴羽·工程师的硬核成长指南.md
    │   └── 转型Agent全栈工程师：企业级知识库项目（神光）.md
    ├── 待学习
    │   └── 学习清单.md
    ├── 待调研
    │   ├── IDE中使用Claude code，能复用IDE的LSP吗.md
    │   ├── Memory Bank调研.md
    │   ├── ai-agent-book.md
    │   ├── gnhf 夜间自主编程编排器.md
    │   ├── workBuddy.md
    │   ├── 【模板】调研模板.md
    │   ├── 如何写好Prompt & 好的Prompt是什么样的.md
    │   ├── 实现github每周前10hub分享.md
    │   ├── 花叔的skill（女娲、橙皮书）.md
    │   └── 调研oh-my-pi.md
    ├── 收藏箱
    │   ├── OpenAI Tokenizer.md
    │   ├── RepoPrompt CE.md
    │   ├── daily_stock_analysis 每日股票分析.md
    │   ├── 【精】Loop Engineering又是啥？一文讲清企业Agent落地的四层工程进化论.md
    │   ├── 【精】一文读懂Harness Engineering.md
    │   ├── 提示词工程.md
    │   └── 用AI Agent做微服务系统设计.md
    ├── 知识沉淀
    │   ├── Agent专家标准
    │   │   ├── Agent专家能力全景.md
    │   │   └── Agent能力自检与补齐路径.md
    │   ├── 小技巧
    │   │   ├── Claude code使用技巧.md
    │   │   └── Obsidian 插件清单与用法.md
    │   ├── 工具技巧
    │   │   ├── Claude code 技巧.md
    │   │   ├── CodeX官方最佳实践.md
    │   │   ├── Codex 技巧.md
    │   │   └── 常用工具及skill.md
    │   ├── 源码系列
    │   │   ├── Claude code源码
    │   │   │   ├── Boris 自己平时怎么用 Claude Code？.md
    │   │   │   ├── CC Session、Transcript、Resume机制.md
    │   │   │   ├── CC agent如何修改代码.md
    │   │   │   ├── CC 上下文压缩机制.md
    │   │   │   ├── CC 多Agent机制.md
    │   │   │   ├── CC 实现修改文件的 approve、reject及代码回退.md
    │   │   │   ├── CC 记忆机制.md
    │   │   │   ├── CC主循环Loop机制.md
    │   │   │   ├── CC代码检索机制.md
    │   │   │   ├── CC工具机制.md
    │   │   │   ├── CC面试题.md
    │   │   │   ├── Claude Code 提示词部分.md
    │   │   │   ├── Claude Code 源码学习大纲.md
    │   │   │   ├── Claude code索引文档.md
    │   │   │   └── Skill 的秘密.md
    │   │   ├── LangChain系列
    │   │   │   ├── LangChain 结构化输出.md
    │   │   │   └── LangSmith.md
    │   │   ├── OpenClaw源码
    │   │   │   ├── OpenClaw 源码学习大纲.md
    │   │   │   ├── openclaw 记忆机制.md
    │   │   │   ├── openclaw 通信渠道机制原理.md
    │   │   │   ├── openclaw与pi-coding- agent的依赖关系.md
    │   │   │   ├── openclaw可插拔机制.md
    │   │   │   ├── openclaw定时任务机制.md
    │   │   │   ├── openclaw工具加载机制.md
    │   │   │   ├── openclaw权限控制机制.md
    │   │   │   └── 索引文件.md
    │   │   ├── Pi Agent源码
    │   │   │   ├── Pi Agent 源码学习大纲.md
    │   │   │   ├── Pi 分层架构设计.md
    │   │   │   ├── Pi-Coding-agent 详解.md
    │   │   │   ├── Pi-agent-core详解.md
    │   │   │   ├── Pi-ai详解.md
    │   │   │   ├── 什么是RPC.md
    │   │   │   └── 索引文档.md
    │   │   ├── RAG系列
    │   │   │   ├── Agentic RAG.md
    │   │   │   ├── OCR.md
    │   │   │   ├── P2-RAG在langchain中的使用记录.md
    │   │   │   ├── P3-RAG.md
    │   │   │   ├── RAG常见问题.md
    │   │   │   ├── 向量数据库对比.md
    │   │   │   ├── 向量检索优化手段之-创建向量索引.md
    │   │   │   ├── 多模态同空间检索.md
    │   │   │   └── 混合检索结果融合与排序方法.md
    │   │   └── 三大 Agent 框架横向对比与面试框架.md
    │   ├── A2A 协议开发者入门.md
    │   ├── Computer Use 是什么.md
    │   ├── Fable 5发布后Claude code删减提示词的规则.md
    │   ├── Function Call 笔记.md
    │   ├── superpower和Grill with doc的区别.md
    │   ├── 多向量数据库对比.md
    │   ├── 如何写好skill.md
    │   ├── 工作流和智能体.md
    │   ├── 提示词工程.md
    │   └── 音频agent.md
    ├── 项目总结
    │   ├── 基于简历的问题猜想
    │   │   ├── LanceDB搭配SQLite.md
    │   │   ├── Vue 同构SSR渲染.md
    │   │   ├── ocean微前端框架.md
    │   │   ├── trigram、FTS5 与 BM25在Continue中的作用.md
    │   │   ├── 基于API文档与代码一致性智能检测工具.md
    │   │   ├── 基于openClaw的MSI端到端智能测试工作流.md
    │   │   ├── 基于团队智能客服助手项目可能的提问.md
    │   │   └── 基于容器桥转MSI桥转码工具.md
    │   ├── 文档一致性调研文档
    │   │   ├── Continue原理揭秘.md
    │   │   ├── LSP与Serena.md
    │   │   ├── Serena 原理揭秘.md
    │   │   ├── 【精】 业内外CodeBase原理分析.md
    │   │   ├── 智能文档校准工具方案.md
    │   │   └── 智能文档校准工具方案调研.md
    │   ├── 智能客服
    │   │   └── RAG在终端前端的应用实践.md
    │   ├── 自动化测试工作流
    │   │   ├── EC 用例评审 — 设计规则速查表.md
    │   │   ├── MSI端到端智能测试应用实践.md
    │   │   ├── Untitled.md
    │   │   ├── 生成测试用例SKill.md
    │   │   ├── 评审EC用例 — 规则与报告模板.md
    │   │   ├── 评审EC用例SKill — 规范符合性说明.md
    │   │   ├── 评审EC用例SKill.md
    │   │   └── 评审可执行测试用例SKill.md
    │   ├── 面试笔记
    │   │   ├── Agent相关面试题.md
    │   │   ├── RAG相关面试题.md
    │   │   ├── 面试公众号.md
    │   │   └── 面试记录.md
    │   ├── KNB桥转MSI桥转码工具.md
    │   ├── 文档代码一致性智能检测工具.md
    │   ├── 智能客服机器人.md
    │   └── 自动化AI研发工作流.md
    └── 🗺️ 学习地图.md
```

## 放置规则

**输入侧（还没消化）**

- `知识库/收藏箱`：先收集、后分流的文章和链接
- `知识库/AI资讯`：资讯、日报、产品观察、趋势记录
- `知识库/待调研`：方向还不确定，先做信息摸底
- `知识库/待学习`：已经决定要学、正在排期或正在学习的内容
- `知识库/待买课程`：还没购买、但值得评估的课程或社群
- `知识库/优秀的github`：值得关注的开源仓库

**消化侧（已经想明白）**

- `知识库/知识沉淀`：已消化的原理笔记与方法论，是知识库的主体
  - `知识沉淀/源码系列`：框架源码解读，按框架分子目录（Claude code / OpenClaw / Pi Agent / LangChain / RAG）
  - `知识沉淀/Agent专家标准`：Agent 领域的能力判别标准、自检清单与补齐路径（回答"什么算专家"，不是"学什么"）
  - `知识沉淀/工具技巧`、`知识沉淀/小技巧`：工具用法、快捷键、最佳实践
- `知识库/项目总结`：做完后的复盘、案例、经验沉淀，按项目分子目录；`面试笔记`、`基于简历的问题猜想` 也在此
- `知识库/小林大模型视频学习总结`：特定课程/视频的学习笔记（按来源归档，不按主题）
- `知识库/复习日记`：复习排期与执行记录

**产出侧**

- `知识库/公众号文章`：对外发布的成稿。带「（微信公众号版）」后缀的是排版润色后的版本，与原稿并存
- `知识库/skills`：本知识库自用的 Claude Skill（`知识库/.claude/skills` 下的是工具型 Skill，非笔记）

## 使用约定

- 新文件优先放进最匹配的现有目录，不要随意新增同义目录。
- 如果内容是“还不确定值不值得学”，放 `待调研`；如果是“确定想学但还没开始”，放 `待学习`。
- 如果内容是“想买但还没买”，统一放 `待买课程`，购买后再移动到 `待学习` 或更具体的主题目录。
- 如果出现新的稳定内容类型，再考虑新增目录，并同步更新本文件。
- 内容的流向是 **输入侧 → 消化侧 → 产出侧**：`收藏箱/待调研` 里的东西一旦想明白，应重写进 `知识沉淀`，而不是留在原地。
- 图片统一放根目录 `图片/`（Obsidian 附件目录）；仅公众号封面等与单篇强绑定的图，可与文章同目录。

## 环境还原

- 换电脑/换终端后，如需还原 Obsidian 插件，参照 `知识库/知识沉淀/小技巧/Obsidian 插件清单与用法.md`：内含全部插件 ID、GitHub 仓库、`community-plugins.json` 内容及安装步骤。新装插件后请同步更新该清单。
