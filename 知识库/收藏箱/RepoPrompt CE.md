# RepoPrompt CE

> 来源：[repoprompt/repoprompt-ce](https://github.com/repoprompt/repoprompt-ce)  
> 核实日期：2026-06-29  
> 状态：收藏待进一步调研

## 一句话总结

RepoPrompt CE 是 RepoPrompt 的开源社区版，一个面向 AI 编程 Agent 的 macOS 原生上下文工程工具和 Agent 编排器，核心目标是让 Agent 在动手改代码前，先拿到经过筛选、可审阅、结构化的仓库上下文。

## 当前仓库定位

- 类型：macOS 原生应用 + MCP CLI / Server
- 主要用途：为 AI 编程 Agent 组织代码仓上下文、运行 Agent 会话、协调多工具工作流
- 技术栈：Swift / Swift Package
- 许可证：Apache-2.0
- 平台要求：macOS 26+
- 安装入口：
  - Homebrew：`brew tap repoprompt/repoprompt-ce && brew install --cask repoprompt-ce`
  - 本地运行：双击 `Launch RepoPrompt CE.command`
  - 本地生产构建：双击 `Install RepoPrompt CE Local Production.command`

## 核心功能

### 1. 上下文工程

RepoPrompt CE 可以从以下来源组装给 AI Agent 使用的上下文：

- 文件内容
- CodeMaps
- 仓库结构
- Git diffs

它强调“focused, reviewable context”，也就是把大仓库里真正相关的内容挑出来，并在交给 Agent 前可人工审阅。

### 2. Agent 编排

RepoPrompt CE 不只是复制上下文，还提供 Agent harness：

- 运行和协调 CLI-backed coding agents
- 管理 Agent session
- 通过共享的 macOS 原生界面观察和组织 Agent 工作
- 让不同 MCP-compatible 客户端或 CLI Agent 接入同一个仓库上下文

### 3. MCP Server 与 CLI 集成

仓库内置 MCP server / CLI 能力，可以让外部 MCP 客户端或命令行 Agent：

- 搜索仓库
- 检查文件
- 选择和整理上下文
- 运行 Agent 会话
- 通过 MCP 工具和 RepoPrompt CE 的原生界面协作

### 4. 多根工作区

支持 multi-root workspace，可以在一个工作区里同时处理：

- 多个相关代码仓
- 包目录
- 文档目录

这类能力适合 monorepo、多仓联动项目，或“代码 + 文档 + 测试资产”一起给 Agent 分析的场景。

### 5. App 管理的 Git Worktree

RepoPrompt CE 可以为 MCP 工具和 Agent Mode 创建 Git worktree。它还支持通过 `.worktreeinclude` 把主 checkout 中被 Git ignore 的本地配置文件复制到 app-managed worktree，例如：

- `.env.local`
- `config/secrets.json`
- 本地证书目录

这个设计适合让 Agent 在隔离 worktree 中工作，同时保留必要的本地运行环境。

## 适合使用的场景

- 想把大仓库中“刚好够用”的上下文交给 Claude、Codex、Cline、Cursor 等 AI 编程工具
- 想在 Agent 动手前审阅它能看到什么上下文，减少无关文件和 Token 浪费
- 需要同时处理多个相关仓库或文档目录
- 希望通过 MCP 把仓库搜索、文件检查、上下文整理能力暴露给外部 Agent
- 想让 Agent 在独立 Git worktree 中运行，降低污染主工作区的风险

## 与现有工具的关系

RepoPrompt CE 更像“上下文 IDE / Agent 编排台”，不是单纯的代码编辑器：

- 与 Cursor / Codex / Claude Code：偏互补，负责准备、筛选、审阅上下文，再交给 Agent 执行。
- 与 Repomix：都关注仓库上下文打包，但 RepoPrompt CE 更强调 macOS 原生 UI、MCP、Agent session 和 worktree 编排。
- 与 Cline / Roo Code：Cline 更偏 VS Code 内 Agent 执行，RepoPrompt CE 更偏外部上下文工程和跨 Agent 编排。

## 后续调研点

- macOS 26+ 门槛是否影响当前机器和团队可用性
- MCP 工具列表、权限模型、隐私边界是否足够清晰
- Agent Mode 支持哪些 provider / CLI Agent，是否能稳定接入 Codex、Claude Code、Cline
- CodeMaps 的生成质量，以及对大型 TypeScript / Java / iOS / Android 仓库的效果
- Worktree + `.worktreeinclude` 对本地密钥和环境文件的安全边界
- 与当前知识库里的“智能文档校准工具方案”是否能结合，用作源码上下文管理或多仓分析入口

## 初步判断

值得继续调研。它解决的问题和“让 AI 更准确理解代码仓库”高度相关，尤其适合需要多仓、多端、多 Agent 协作的代码分析任务。短板是平台要求较高，目前更偏 macOS 生态，是否适合团队推广还需要实际试用确认。

