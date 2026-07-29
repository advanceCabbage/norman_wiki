## 一、核心模块功能
> PI 的主要架构层都以独立 npm 包提供，位于同一个 npm workspaces 单仓库中。workspaces 解决的是：**代码放在一起协同开发，但每层仍保持独立包边界、独立版本、独立发布与独立复用**


#### 1.1  `pi-ai`（核心模块）
功能介绍：最底层的 LLM 接入与统一抽象层，**适配抹平多厂商 LLM API 的消息、工具调用和流式响应差异格式**，适配 30+模型供应商

#### 1.2 `pi-agent-core`（核心模块）
功能介绍：**通用 Agent 执行内核**，包括：Loop 循环、工具调用、压缩、skill 加载、系统提示词加载及工具生命周期事件

#### 1.3 `pi-coding-agent`（核心模块）
功能介绍： **`pi` CLI 与 SDK 的应用层**。负责参数解析、配置、模型选择与认证、资源加载、内置文件/Shell 工具、会话树与压缩、扩展/技能/主题、交互 TUI、Print/JSON/RPC 模式，并把这些能力编排为编码 Agent

#### 1.4 `pi-tui`
功能介绍：可复用终端界面库，不与 Pi 生态绑定，可复用于任何 Agent 框架。在终端命令场景下可用的界面库，支持：自动补全、主题、图片渲染、终端输入等

#### 1.5 `pi-storage-sqlite-node`
功能介绍：基于 Node sqlite 实现的会话存储功能，可以存储会话、消息条目等

#### 1.6 `pi-server`
功能介绍：实验性本地服务层。通过 IPC 管理多个 coding-agent RPC 子进程，提供实例创建、状态查询、停止、事件流转发和元数据持久化；可集成 Radius 在线状态。它不直接执行模型调用

## 二、架构层依赖关系图谱

#### 2.1 整体架构层依赖关系
```JSON
pi-server
  └─→ pi-coding-agent
        ├─→ pi-agent-core
        │     └─→ pi-ai
        ├─→ pi-ai
        └─→ pi-tui

pi-storage-sqlite-node
  ├─→ pi-agent-core
  └─→ pi-ai

pi-tui       # 不依赖其他 PI 模块，最底层模块
pi-ai        # 不依赖其他 PI 模块，最底层模块

```
#### 2.2 核心三模块架构依赖

```JSON
pi-coding-agent
        ├─→ pi-agent-core
        │     └─→ pi-ai
        └─→  pi-ai
```
- pi-coding-agent 同时依赖于 pi-agent-core 和 pi-ai
- pi-agent-core 依赖于pi-ai