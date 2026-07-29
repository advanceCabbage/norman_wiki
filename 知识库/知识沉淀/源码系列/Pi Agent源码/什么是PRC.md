## 一、PRC 通用概念
**RPC = Remote Procedure Call（远程过程调用**）——让一个程序像调用本地函数一样去调用另一个进程/机器上的函数，中间的序列化、传输、反序列化对调用方透明。常见实现有 gRPC、JSON-RPC、Thrift 等。**PRC 仅仅是约定的协议，无实际的约束效果，需要达成共识遵守**

## 二、三类 PRC 的对比
#### 2.1 JSONPRC

**制定方**：2010 年 3 约定稿，JSON-RPC Working Group —— 社区规范，无公司背书

**使用场景**
-  编辑器 ↔ 语言服务，示例：LSP（Language Server Protocol），JSON-RPC 2.0 + Content-Length 头，走 stdio
- AI Agent ↔ 工具，示例：MCP（Model Context Protocol），stdio + HTTP 双 transport
- IDE ↔ 调试器，示例：DAP（Debug Adapter Protocol）
- 浏览器可直调的后端，示例：不需要 proxy，fetch 直接发
- 区块链节点 API，示例：以太坊 eth_call、比特币 getblockchaininfo 全是 JSON-RPC

**什么时候选它**：需要跨语言、跨组织、要能人肉调试、接口不多且不追求极致性能、尤其是走 stdio 而非网络的时候。

**JSONPRC 格式**
请求：jsonrpc + method + params（可选）+ id（可选）
```JSON
{
  "jsonrpc": "2.0",
  "method": "hotel.getDetail",
  "params": {
    "hotelId": "h_1001"
  },
  "id": 1 // 不传Id表示通知消息无需接受回复
}
```
响应：jsonrpc + result 或 error + id
```JSON
{
  "jsonrpc": "2.0",
  "result": {
    "name": "西安钟楼酒店"
  },
  "id": 1
}
```

#### 2.2 gRPC

**制定方**：Google 于 2015 年制定，强依赖于 HTTP 2.0

**使用场景**
- **微服务间调用**，示例：内网东西向流量的事实标准 
- **Kubernetes 生态**，示例：K8s 自身、etcd、Envoy xDS、containerd 全用 gRPC
- **实时双向通信**，示例：双向流适合聊天、协作、遥测上报
- **移动端 ↔ 后端**，示例：Protobuf 省流量，对移动网络友好

**什么时候选它**：内网服务间通信、团队多语言、接口数量大且频繁演进（需要编译期契约保护）、需要流式、需要成熟的超时/重试/负载均衡/可观测性生态。

**什么时候别选**：给浏览器直接调、要走 stdio、只有三五个接口、团队没精力维护 protoc 构建链。

#### 2.3 Thrift 

**制定方**：Facebook 2007 制定，不绑定于网络环境

**使用场景**：
- **多语言混合的大型后端**，示例：Facebook 早期、字节跳动内部大量使用（Kitex 框架兼容 Thrift IDL）
- **数据库/存储的客户端接口**，示例：HBase、Cassandra（早期 Thrift API）、Hive Server
- **需要非常规 Protocol/Transport 组合**，示例：落盘归档、内存直通、协议渐进迁移

**什么时候选它**：已有 Thrift 存量（最常见的理由）、需要在编码或传输上做非标准组合、语言覆盖要求极广（20+ 语言）。

**什么时候别选**：新项目基本不推荐——生态活跃度、文档质量、各语言实现成熟度都明显落后于 gRPC，且无原生流式支持。

## 三、PI 中的 PRC 模式

#### 3.1 Pi Interactive 模式没有使用 RPC 通信模式

**pi-tui 不是客户端，pi-coding-agent 不是服务端，它们之间没有任何 RPC 通信。**
真相是： pi-tui 是一个终端渲染库，被 coding-agent 直接 import 进同一个进程。它们之间是普通的函数调用，零序列化、零 IPC
Interactive 模式：单进程内的通信

#### 3.2 PRC 模式，使用的 PRC 通信
RPC 模式：这时候才有客户端/服务端，
客户端：外部宿主程序（任意语言），作用是，发命令、收事件、自己渲染 UI 
服务端：pi --mode rpc 子进程 ，作用是，跑 agent 业务逻辑，headless

##### 3.2.1 通信机制
**Interactive 模式**
用户敲字 → 屏幕更新，全程在一个进程内：
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

**RPC 模式**
多了两次序列化跨越：
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

注意中间那一段是完全一样的——session.prompt() 之后的所有逻辑，两种模式共用。RPC 只是在最外面套了一层"序列化 + 管道"。


| 问题             | 答案                                             |
| -------------- | ---------------------------------------------- |
| pi-tui 是客户端吗？  | ❌ 不是。它是同进程内的渲染库，无 bin，无法独立运行                   |
| 它们用 JSONL 通信吗？ | ❌ 不。用 subscribe 回调（下行）+ 直接方法调用（上行）             |
| 那 RPC 的客户端是谁？  | 外部宿主程序：Python 脚本 / IDE 插件 / Web 后端 / RpcClient |
| RPC 的服务端是谁？    | pi --mode rpc 子进程，里面没有 pi-tui                  |
| 两种模式的关系？       | 同一个 AgentSession 事件源，TUI 和 RPC 是两个平行的"渲染后端"    |
| 有反向调用吗？        | 有，扩展 UI 子协议：pi → 宿主                            |

##### 3.2.2 通信 json 数据结构
  **① 提问（宿主 → pi，写入 stdin）**
  {"id":"req-1","type":"prompt","message":"统计当前项目有多少个 .ts 文件"}
  ▎ 一行一条，以 \n 结尾。id 可选，用于和响应配对。

**② 回复（pi → 宿主，从 stdout 读出）**
回复分两部分：先是一条命令响应，然后是持续推送的事件流。
**第一部分：命令响应（带 id）**
{"id":"req-1","type":"response","command":"prompt","success":true}
▎ success: true 只表示"命令被接受"，不代表任务完成。真正的结果在后面的事件流里。
**第二部分：事件流（不带 id）**
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"user","content":"统计当前项目有多少个 .ts 文件","timestamp":1733234560000}}
{"type":"turn_end","message":{"role":"assistant","stopReason":"stop"},"toolResults":[]}
{"type":"agent_end","messages":[],"willRetry":false}
{"type":"agent_settled"}

###### 3.2.2.1 事件流不带 ID 会导致消息接收错乱吗？
结论先行：在正常实现下不会错乱，因为 pi 用了三层保障，而且在真正会并发的地方，它其实都给了 id。
- 保障一：不允许并发的 agent run
- 保障二：stdout 是单一有序管道
- 保障三：用"括号定界"代替 id 配对，事件不靠 id 关联，靠严格成对的嵌套结构，客户端仅需维护一个栈式状态机：
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

事件不带 id 不是疏漏，是因为它们天然串行——单进程、单会话、单 run、单管道、有序 emit。而在唯一真正会并发的地方（并行工具执行、多个 pending 的扩展 UI 请求、多条 in-flight 命令），pi 都老老实实给了 toolCallId / id。

这其实和 JSON-RPC 的设计哲学一致：notification 不带 id，request 才带——id 的成本（客户端要维护配对表）只在真正需要配对时才付出。