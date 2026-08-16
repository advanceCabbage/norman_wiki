# Function Calling、Skill、MCP 这三个有什么区别

## 一、核心概念

**Function Calling** 是模型 ↔ 运行时的接口约定：在请求里用 JSON Schema 声明工具，模型输出结构化的调用意图（调哪个、传什么参），**执行由宿主程序完成**。

**MCP** 是宿主集成协议（JSON-RPC 2.0）：把数据库、API 封装成标准 Server，向宿主暴露 Tools / Resources / Prompts。核心价值是**一次实现、跨客户端复用**。模型看不见 MCP，是宿主把 MCP 的工具定义翻译成模型 API 的 tool 格式。

**Skill** 是喂给模型的**可按需加载的规程包**：一个带 SKILL.md 的文件夹，description 常驻上下文做路由，正文和脚本在判定相关后才加载。它解决的是「长尾知识如何不永久占用上下文」。

这三者在典型 Agent 里会同时出现，但没有硬依赖：本地函数 + Function Calling 完全可以不要 MCP；MCP Inspector 里人手点工具，全程零模型；纯知识型 Skill 一个工具都不调。

## 二、分别解决的问题

**Function Calling** —— 解决「模型如何把『我要用某个工具』这件事，表达成程序能可靠解析的结构化输出」，概念由 OpenAI 公司提出。

**MCP** —— 解决「一个外部能力如何只实现一次，就能被任意宿主应用接入并复用」，概念由 Anthropic 公司提出。

**Skill** —— 解决「一套只在少数场景用得上的长篇规程，如何做到不常驻上下文、却又能在真正需要时被准确唤起」，概念由 Anthropic 公司提出。

## 三、MCP 中的 Resources 和 Prompts 使用场景

### 3.1 Resources

**功能**：让 Server 用 URI 暴露一批**只读数据**（文件、表结构、日志），宿主可以列目录、按需读取，还能订阅变更。

**解决的问题**：**有些数据是用户/应用早就知道要哪份的，不该让模型去「决定调哪个工具取」。**

### 3.2 Prompts

**功能**：Server 附带的一组**用户可调用的命令模板**，支持传参，返回的是组装好的完整对话消息（可内嵌 Resource 内容）。

**解决的问题**：**用好一个工具所需的那套提示词，不该让每个用户自己重新摸索。**

## 四、Function Call 的结构形式

一个 Function Call 工具定义通常包含：

- <span style="display:inline;color:#35b378;font-weight:bold;">`type`</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：工具类型，通常是 `function`。</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">`name`</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：函数名，模型会用这个名字发起调用。</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">`description`</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：函数用途说明，影响模型什么时候选择该函数。</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">`parameters`</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：JSON Schema，描述函数参数结构。</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">`strict`</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：是否要求模型严格遵守 schema。</span>

示例：

```json
{
  "type": "function",
  "name": "get_order",
  "description": "Get order details by order id.",
  "parameters": {
    "type": "object",
    "properties": {
      "order_id": {
        "type": "string",
        "description": "The order id to query."
      }
    },
    "required": ["order_id"],
    "additionalProperties": false
  },
  "strict": true
}
```

这里需要注意：

- 传给模型的是「函数定义」或「工具定义」，不是函数执行结果。
- 模型返回的才是一次具体的 Function Call。
- 真正执行函数的是应用程序代码，而不是模型本身。
