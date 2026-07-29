# 什么是 RPC？从 JSON-RPC、gRPC、Thrift 到 Pi 的 RPC 模式

## 一、RPC 的通用概念

**RPC = Remote Procedure Call（远程过程调用）**。它让一个程序能够像调用本地函数一样，调用另一个进程或另一台机器上的函数；中间的序列化、传输与反序列化对调用方透明。

常见实现包括 gRPC、JSON-RPC 和 Thrift 等。RPC 仅是一套约定协议，本身没有实际的强制约束效果，需要通信双方达成共识并共同遵守。

## 二、三类 RPC 的对比

### 2.1 JSON-RPC

**制定方**：2010 年 3 月约定稿，JSON-RPC Working Group；属于社区规范，无公司背书。

**使用场景**

- 编辑器 ↔ 语言服务：例如 LSP（Language Server Protocol），使用 JSON-RPC 2.0 + `Content-Length` 头，走 `stdio`。
- AI Agent ↔ 工具：例如 MCP（Model Context Protocol），使用 `stdio` + HTTP 两种 transport。
- IDE ↔ 调试器：例如 DAP（Debug Adapter Protocol）。
- 浏览器可直调的后端：不需要 proxy，直接通过 `fetch` 发送请求。
- 区块链节点 API：例如以太坊 `eth_call`、比特币 `getblockchaininfo`，均使用 JSON-RPC。

**什么时候选它**：需要跨语言、跨组织，接口可被人工调试；接口不多且不追求极致性能，尤其是走 `stdio` 而非网络时。

**JSON-RPC 格式**

请求由 `jsonrpc`、`method`、`params`（可选）和 `id`（可选）组成。未传 `id` 时，表示无需接收回复的通知消息。

```json
{
  "jsonrpc": "2.0",
  "method": "hotel.getDetail",
  "params": {
    "hotelId": "h_1001"
  },
  "id": 1
}
```

响应由 `jsonrpc`、`result` 或 `error`，以及 `id` 组成。

```json
{
  "jsonrpc": "2.0",
  "result": {
    "name": "西安钟楼酒店"
  },
  "id": 1
}
```

### 2.2 gRPC

**制定方**：Google 于 2015 年制定，强依赖于 HTTP/2。

**使用场景**

- **微服务间调用**：内网东西向流量的事实标准。
- **Kubernetes 生态**：K8s 自身、etcd、Envoy xDS、containerd 都使用 gRPC。
- **实时双向通信**：双向流适合聊天、协作和遥测上报。
- **移动端 ↔ 后端**：Protobuf 更省流量，对移动网络友好。

**什么时候选它**：内网服务间通信、团队使用多种语言、接口数量大且频繁演进（需要编译期契约保护），或需要流式能力，以及成熟的超时、重试、负载均衡、可观测性生态。

**什么时候别选**：需要让浏览器直接调用、需要走 `stdio`、只有三五个接口，或团队没有精力维护 `protoc` 构建链时。

### 2.3 Thrift

**制定方**：Facebook 于 2007 年制定，不绑定网络环境。

**使用场景**

- **多语言混合的大型后端**：Facebook 早期、字节跳动内部大量使用；Kitex 框架兼容 Thrift IDL。
- **数据库 / 存储的客户端接口**：例如 HBase、Cassandra（早期 Thrift API）、Hive Server。
- **需要非常规 Protocol / Transport 组合**：例如落盘归档、内存直通、协议渐进迁移。

**什么时候选它**：已有 Thrift 存量（最常见的理由）；需要在编码或传输上做非标准组合；语言覆盖要求极广（20+ 种语言）。

**什么时候别选**：新项目基本不推荐。其生态活跃度、文档质量和各语言实现成熟度都明显落后于 gRPC，且没有原生流式支持。

## 三、Pi 中的 RPC 模式

### 3.1 Pi Interactive 模式没有使用 RPC 通信

**`pi-tui` 不是客户端，`pi-coding-agent` 不是服务端；它们之间没有任何 RPC 通信。**

`pi-tui` 是一个终端渲染库，被 `coding-agent` 直接 `import` 进同一个进程。二者之间是普通函数调用：零序列化、零 IPC。

Interactive 模式本质上是单进程内通信。

### 3.2 RPC 模式才使用 RPC 通信

在 RPC 模式下，才存在客户端与服务端：

- **客户端**：外部宿主程序（任意语言），负责发送命令、接收事件、自己渲染 UI。
- **服务端**：`pi --mode rpc` 子进程，负责运行无界面的 Agent 业务逻辑。

#### 3.2.1 通信机制

**Interactive 模式**：用户输入到屏幕更新，全程在同一个进程内完成。

```text
用户按键
  → pi-tui 的 stdin-buffer 解析（含 Kitty 键盘协议等）
  → Editor 组件更新
  → 回车 → InteractiveMode 取出文本
  → session.prompt(text)                    ← 直接方法调用
  → AgentSession → Agent → provider HTTP 请求
  → 流式响应回来，Agent 触发事件
  → AgentSession 遍历 _eventListeners 数组   ← 同一个对象引用传递
  → InteractiveMode.handleEvent(event)
  → 更新组件树 + this.ui.requestRender()
  → pi-tui 差分算法算出最小转义序列
  → 写入 process.stdout
  → 终端刷新
```

**RPC 模式**：额外多了两次序列化跨越。

```text
宿主构造命令对象
  → JSON.stringify + "\n"
  → 写入子进程 stdin                          ← ① 序列化边界
  → pi 的 JSONL reader 按 \n 切分 + JSON.parse
  → runRpcMode 分发到 session.prompt(text)   ← 落回同样的方法调用
  → AgentSession → Agent → provider
  → 事件触发，遍历 _eventListeners
  → runRpcMode 的回调收到 event
  → serializeJsonLine(event) 写 stdout       ← ② 序列化边界
  → 宿主的 JSONL reader 解析
  → 宿主自己决定怎么渲染
```

注意，中间部分完全相同：`session.prompt()` 之后的所有逻辑，两种模式共用。RPC 只是在最外层套了一层“序列化 + 管道”。

| 问题 | 答案 |
| --- | --- |
| `pi-tui` 是客户端吗？ | ❌ 不是。它是同进程内的渲染库，无 bin，无法独立运行。 |
| 它们用 JSONL 通信吗？ | ❌ 不。用 `subscribe` 回调（下行）+ 直接方法调用（上行）。 |
| 那 RPC 的客户端是谁？ | 外部宿主程序：Python 脚本 / IDE 插件 / Web 后端 / RpcClient。 |
| RPC 的服务端是谁？ | `pi --mode rpc` 子进程，里面没有 `pi-tui`。 |
| 两种模式的关系？ | 同一个 `AgentSession` 事件源，TUI 和 RPC 是两个平行的“渲染后端”。 |
| 有反向调用吗？ | 有，扩展 UI 子协议：Pi → 宿主。 |

#### 3.2.2 通信 JSON 数据结构

**① 提问（宿主 → Pi，写入 stdin）**

```json
{"id":"req-1","type":"prompt","message":"统计当前项目有多少个 .ts 文件"}
```

一行一条，以 `\n` 结尾。`id` 可选，用于与响应配对。

**② 回复（Pi → 宿主，从 stdout 读取）**

回复分两部分：先是一条命令响应，然后是持续推送的事件流。

**第一部分：命令响应（带 `id`）**

```json
{"id":"req-1","type":"response","command":"prompt","success":true}
```

`success: true` 只表示“命令被接受”，不代表任务完成。真正的结果在后续事件流中。

**第二部分：事件流（不带 `id`）**

```json
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"user","content":"统计当前项目有多少个 .ts 文件","timestamp":1733234560000}}
{"type":"turn_end","message":{"role":"assistant","stopReason":"stop"},"toolResults":[]}
{"type":"agent_end","messages":[],"willRetry":false}
{"type":"agent_settled"}
```

##### 3.2.2.1 事件流不带 ID 会导致消息接收错乱吗？

结论先行：在正常实现下不会错乱。Pi 用了三层保障；而在真正会并发的地方，它都提供了 `id`。

- **保障一**：不允许并发的 Agent run。
- **保障二**：`stdout` 是单一有序管道。
- **保障三**：用“括号定界”代替 `id` 配对。事件不靠 `id` 关联，而是依靠严格成对的嵌套结构；客户端仅需维护一个栈式状态机。

```text
agent_start ─────────────────────────────────┐
  turn_start ───────────────────────────┐    │
    message_start ──┐                   │    │
      message_update × N                │    │
    message_end ────┘                   │    │
    tool_execution_start ──┐            │    │
      tool_execution_update × N         │    │
    tool_execution_end ────┘            │    │
    message_start/message_end (toolResult)   │
  turn_end ─────────────────────────────┘    │
  turn_start ... turn_end                    │
agent_end ───────────────────────────────────┘
agent_settled   ← 整个 run 彻底结算
```

事件不带 `id` 不是疏漏，而是因为它们天然串行：单进程、单会话、单 run、单管道、有序 emit。在唯一真正会并发的地方——并行工具执行、多个 pending 的扩展 UI 请求、多条 in-flight 命令——Pi 都提供了 `toolCallId` / `id`。

这与 JSON-RPC 的设计哲学一致：notification 不带 `id`，request 才带。`id` 的成本（客户端维护配对表）只在真正需要配对时才付出。
