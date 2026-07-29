## 一、功能解析
`pi-ai` 是一个面向 Agent 场景的多 Provider LLM 网关层：它通过统一领域模型、Provider 路由和协议适配，将不同厂商的认证、流式响应、工具调用、上下文兼容与成本统计收敛为一致接口

- 统一不同厂商模型 API 的请求、响应、消息和停止原因

- 统一工具定义、流式工具调用参数、工具调用 ID 与工具结果

- 对不支持视觉输入的模型，将图片替换为文本占位

- 将不同厂商的流式协议归一为统一事件流：文本、思考、工具调用、完成、错误

- 支持 38 个 Provider，复用 10 类文本协议适配器（例如 openAI 的 provider 为 openai、openai-codex）
#### 1.1 理解 10 类文本协议适配器
**文本协议适配器**可以理解为：把 PI 的统一对话对象，翻译成某一类厂商文本模型 API 的请求格式；再把厂商的流式响应翻译回 PI 的统一事件流。
它主要做五件事：
1. 转换系统提示词、历史消息和图片输入
2. 转换工具定义与工具结果
3. 发送流式请求
4. 将文本、thinking、工具参数分片转换成统一事件
5. 统一结束原因、Token 用量、缓存用量和错误

举例智谱 AI 的适配器代码
**PI 内部工具**：
```JSON
{
  name: "read_file",
  description: "Read a file",
  parameters: Type.Object({
    path: Type.String(),
  }),
}
```
发送给 Z.AI 时，`openai-completions` 适配器转换为：
```json
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "read_file",
      "description": "Read a file",
      "parameters": {
        "type": "object",
        "properties": {
          "path": { "type": "string" }
        },
        "required": ["path"]
      }
    }
  }]
}
```
Z.AI 流式返回的 `delta.content`、`delta.tool_calls`，会被转换成 PI 的：
```json
text_delta
toolcall_start
toolcall_delta
toolcall_end
done
```