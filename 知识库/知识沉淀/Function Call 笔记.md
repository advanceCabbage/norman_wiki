

## 1. Function Call 是什么

Function Call，也常被称为 Tool Calling，是一种让大模型调用外部能力的机制。

它的核心不是“模型真的执行函数”，而是：

1. 开发者把可用函数的名称、用途、参数结构传给大模型。
2. 大模型判断当前任务是否需要调用某个函数。
3. 如果需要，大模型返回一个结构化的函数调用请求，包括函数名和参数。
4. 应用程序接收这个请求，真正执行对应代码。
5. 应用程序把函数执行结果再传回大模型。
6. 大模型基于函数结果继续生成最终回答，或继续请求调用其他函数。

因此，Function Call 的本质是：

> 让模型把自然语言任务转成“应该调用哪个函数，以及用什么参数调用”的结构化请求。

它适合用于接入外部实时数据、业务系统、数据库、内部 API、确定性计算、订单操作、检索工具等。

## 2. Function Call 的结构形式

一个 Function Call 工具定义通常包含：

- `type`：工具类型，通常是 `function`。
- `name`：函数名，模型会用这个名字发起调用。
- `description`：函数用途说明，影响模型什么时候选择该函数。
- `parameters`：JSON Schema，描述函数参数结构。
- `strict`：是否要求模型严格遵守 schema。

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

- 传给模型的是“函数定义”或“工具定义”，不是函数执行结果。
- 模型返回的才是一次具体的 function call。
- 真正执行函数的是应用程序代码，而不是模型本身。

模型可能返回类似：

```json
{
  "type": "function_call",
  "name": "get_order",
  "arguments": "{\"order_id\":\"A123\"}",
  "call_id": "call_xxx"
}
```

应用程序再根据 `name` 找到真实函数，根据 `arguments` 解析参数并执行。

## 3. 在大模型中如何使用 Function Call

一次典型调用会分成两个阶段：先让模型决定是否调用函数，再把函数结果交回模型。

第一轮请求：把用户问题和可用函数定义传给模型。

```ts
const response = await client.responses.create({
  model: "gpt-5.5",
  input: "帮我查一下订单 A123 的状态",
  tools: [
    {
      type: "function",
      name: "get_order",
      description: "Get order details by order id.",
      parameters: {
        type: "object",
        properties: {
          order_id: { type: "string" }
        },
        required: ["order_id"],
        additionalProperties: false
      },
      strict: true
    }
  ]
});
```

如果模型认为需要查订单，它不会直接回答，而是返回一个工具调用请求：

```json
{
  "type": "function_call",
  "name": "get_order",
  "arguments": "{\"order_id\":\"A123\"}",
  "call_id": "call_xxx"
}
```

然后应用程序执行真实函数：

```ts
const args = JSON.parse(toolCall.arguments);
const result = await getOrder(args.order_id);
```

第二轮请求：把函数结果传回模型。

```ts
const finalResponse = await client.responses.create({
  model: "gpt-5.5",
  input: [
    toolCall,
    {
      type: "function_call_output",
      call_id: toolCall.call_id,
      output: JSON.stringify(result)
    }
  ],
  tools
});
```

模型拿到函数结果后，生成自然语言回答：

```text
订单 A123 当前状态是已发货，预计明天下午送达。
```

## 4. Function Call 的执行顺序

完整执行顺序如下：

```text
用户输入
  -> 应用程序把用户输入 + tools/function schema 发送给模型
  -> 模型判断是否需要调用函数
  -> 如果不需要：模型直接返回自然语言回答
  -> 如果需要：模型返回 function_call，包括函数名、参数、call_id
  -> 应用程序解析 function_call
  -> 应用程序执行真实函数/API/数据库查询
  -> 应用程序把 function_call_output 传回模型
  -> 模型基于工具结果继续回答
  -> 如果还需要更多工具，继续进入下一轮工具调用
```

可以把 Function Call 理解为一个应用程序控制的 agent loop：

```text
while 模型请求调用函数:
  执行函数
  把函数结果交回模型

输出最终回答
```

## 5. 每轮对话是否必须传入 Function Call

更准确地说，每轮不是传入“Function Call”，而是传入 `tools`，也就是函数定义。

实践规则：

> 只要这一轮希望模型有能力调用某些函数，就应该在这次请求里传入对应的 `tools`。

如果某一轮没有传入 `tools`：

- 模型不会知道这些函数当前可用。
- 模型不能返回对应的 function call。
- 模型只能基于已有上下文直接生成文本回答。
- 即使前一轮传过函数定义，也不应假设模型在后续请求中自动拥有这些工具。

因此，常见工程做法是：

- 把工具定义写成常量或注册表。
- 每次需要工具能力的模型请求都复用同一批 `tools`。
- 如果这一轮明确不允许调用工具，就不传 `tools`，或设置工具选择策略禁止调用。

示例：

```ts
const tools = [getOrderTool, refundOrderTool, searchDocsTool];

async function askModel(input: string) {
  return client.responses.create({
    model: "gpt-5.5",
    input,
    tools
  });
}
```

## 6. 注意事项和优化点

### 开启 strict mode

建议给函数定义设置 `strict: true`，这样模型返回的参数会更可靠地符合 JSON Schema。

配合 strict mode 时，schema 通常需要：

- 对象设置 `additionalProperties: false`。
- `properties` 中的字段都列入 `required`。
- 可选字段用 `["string", "null"]` 之类的方式表达。

### 函数说明要写清楚

`name` 和 `description` 会直接影响模型是否选对工具。描述里应该说明：

- 这个函数做什么。
- 什么时候应该使用。
- 什么时候不应该使用。
- 参数格式是什么。
- 返回结果代表什么。

### 不要把模型当作执行环境

模型只负责产生调用意图和参数。

权限校验、参数校验、业务规则、数据库访问、HTTP 请求、副作用操作都应该在应用程序侧完成。

### 控制工具数量

一次性暴露太多工具会降低模型选择准确率，也会增加上下文成本。

常见做法：

- 只传入当前场景需要的工具。
- 把大工具集按业务域拆分。
- 对低频工具做延迟加载或工具检索。

### 对有副作用的函数加保护

例如退款、删除数据、发邮件、创建订单等函数，应在应用程序侧加确认、权限和审计。

不要仅凭模型返回的 function call 就直接执行高风险操作。

## 参考出处

- OpenAI Function Calling Guide: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI Conversation State Guide: https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI Responses API Migration Guide: https://developers.openai.com/api/docs/guides/migrate-to-responses
- Anthropic Tool Use Overview: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
