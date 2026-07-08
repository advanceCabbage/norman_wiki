## 一、问题记录
- openclaw 的底层技术原理
- openclaw 带来的思考、沉淀
## 二、openclaw gateway 是如何工作的？
![[Pasted image 20260707145105.png]]
本质上是一个 webSocket 服务
- webSocket 相关知识补充
- 大模型和前端流式输出消息用的协议是 SSE，看下 SSE 的定义是什么？SSE 协议和 webSocket 是什么关系
- 进程、容器、虚拟机、沙箱 隔离机制等级
	- L1 同进程：三个函数共享一切：内存、变量、异常；一个函数崩溃整个进程崩溃
	- L2 独立进程：内存独立、PID 独立，但都能看到同一个文件系统；进程 A 崩溃时 B 不受影响，但 A 能读到 B 的文件
	- L3 容器（Docker）：各自一套文件系统、网络、进程空间；独立机器、文件，但共享内核
	- L4 虚拟机：内核都是各自独立，隔离最彻底也最重

##### 2.1 Gateway 做哪些事情
- **路由**：决定这条消息归谁，按渠道、按用户 session 进行消息路由
- **鉴权**：权限问题，哪些用户具备对应的权限，举例：owner 具备删除权限，其他人不具备
- **广播**：从 agentRuntime 获取到的消息，发送给对应的终端。例如，将从飞书来的消息发送回飞书
- **状态版本**：目的断线重连接不丢消息，例如：飞书渠道断开了，断开期间 agentRuntime 产生了三条消息，而后飞书渠道正常连接了，此时依旧能将这三条消息正常发送到飞书
**一句话总结：Gateway 是无 AI 的、有状态的、协议层死逻辑**
##### 2.2 gateway 三种帧消息类型
![[Pasted image 20260707151327.png]]
- Reqest: 客户端向服务端发送消息
- Result：服务端向客户端回复消息
- Event：本质也是服务端向客户端回复消息，只是此时没有客户端主动触发，代表场景：定时任务
##### 2.3 

## 三、openClaw 关键名词解释
- **Gateway** 本机用户枢纽跑在 127.0.0.1 上，然后用 WebSocket 串联所有组件
- **Channel** 把微信飞书的外部 IM 变成 Agent 的入口通道适配器
- **Node** 你的每台设备都以 Node 身份连回 gateway 贡献工具能力
- **Agent Runtime** 调度模型、跑 Agent Loop 、调工具

## 四、openClaw 的通信渠道协议是如何设计的
#### 4.1 通信协议具备哪些字段，以致于各个渠道都能适配


#### 4.2 渠道类的笔记
- 所有不同渠道接入时，看到的底层工具是一致的
- 各个渠道使用底层工具无需注册
- 渠道特定的工具，依旧需要在工具集中进行注册。例如：飞书渠道想使用飞书文档，是需要在工具集中注册飞书文档工具
## 五、openClaw 的 agent Runtime 是如何运行

#### 5.1 Session 模型
session 生命周期三件事：load 读取存在的 session、create 创建新的 session、reset 清空 session
#### 5.2 Agent Loop 
Agent Loop 本质上是一个 while 循环：模型每轮要么调用工具、要么给出最终答案

###### open claw 中有哪些 Harness 设计？
- 统一、抹平各个模型的调用方式
- ...

**Agent Loop = 上下文组装 -> 模型推理 -> 工具调用 + 结果回注 -> 循环 -> 最终回复 + 记忆写回**

#### 5.3 Runtime 上下文变化

准备 System Prompt 、工具清单、会话历史 、本轮用户输入

#### 5.4 记忆系统
五层记忆系统
- Session Transcript ：本会话用户消息 + 最终助手回复
- Compaction Summary：长 transcript 被压成可续跑摘要
- Memory Search：让模型主动查长期记忆
- Long- term Preferences：用户偏好、身份事实、稳定约束
- Skill/Node Memory ：skill 专属记忆、设备本地状态

**工具返回的信息哪些会记忆？在整个 loop 过程中哪些信息是需要记忆的？**

## 六、工具层
#### 6.1 工具家族概览
![[Pasted image 20260707190506.png]]
#### 6.2 文件系统工具
看似「读文件」是一件小事，实际上 6 个关卡：路径沙箱、审计、分页、patch 写入、结果压缩。
六个关卡依次是：路径解析 -> roots 白名单校验  -> 审计记账  -> 大文件分页摘要  -> patch 写入 + diff 预览  -> 精简回注

- 权限管理
- 上下文管理
- 文件更改的追踪
#### 6.3 playwright 浏览器
- 截图 + OCR 的方案不太准、精度不够高

##### 6.3.1 playwright 是如何实现的？
 a11y tree 不是从 HTML 解析出来的。眼睛是 a11y tree，手是工具调用
 ![[Pasted image 20260707191929.png]]
#### 6.4 Shell 执行
Shell 执行完成后上下文非常长，工具会截断到总字节上限，例如：保留头尾，中间压缩

## 7. 会话沙箱与权限矩阵

![[Pasted image 20260707192734.png]]

## 8. 生态
#### 8.1 Plugin 、Skill、MCP
![[Pasted image 20260707192829.png]]

#### 8.2 ClawHub 技能生命周期
![[Pasted image 20260707193240.png]]


## 9. 为什么 openClaw 火 
![[Pasted image 20260707193609.png]]


## Harnes 
![[Pasted image 20260707193715.png]]