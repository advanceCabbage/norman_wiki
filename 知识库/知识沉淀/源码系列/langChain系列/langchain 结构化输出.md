**背景**：期望大模型能输出指定、约定的 JOSN 格式或数据结构
**核心概念**：部分大模型支持原生结构化输出，例如：openAi、Anthropic、Grok 等模型公司。则在调用大模型时可以指定输出的内容结构。对于不支持原生结构化输出的大模型，LangChain 降级为 `ToolStrategy`：**把你的输出 schema 包装成一个虚拟工具（tool）**，要求模型通过“调用工具”的方式提交结构化参数，而不是输出一段 JSON 文本

**对我的提示**：在此之前我不知道模型可以支持原生结构化的输出，我以为需要使用提示词要求模型输出结构化的内容

#### LangChain 结构化输出语法
- 结构化对象写response_format 参数
- 模型/供应商支持原生 structured output
	- 自动使用 **ProviderStrategy**，把 schema 传给供应商原生 API
- 不支持原生 structured output
	- 自动使用 **ToolStrategy**，将 schema 包装成一个虚拟工具，让模型通过 tool call 传回参数

```



```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent

class ProductReview(BaseModel):
    rating: int | None = Field(ge=1, le=5)
    sentiment: str
    key_points: list[str]

agent = create_agent(
    model="openai:gpt-5.6",
    tools=[...],
    response_format=ProductReview,  # 不要显式写 ProviderStrategy / ToolStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "分析这条评论：..."}]
})

review = result["structured_response"]

```
