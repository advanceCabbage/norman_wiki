# 用 AI Agent 做微服务系统设计

> 来源：宝玉 @dotey（X）
> 链接：https://x.com/dotey/status/2071961238528012358
> 主题：多微服务架构下，如何让 AI Agent 有效地做跨服务的系统设计与编码

## 核心问题

当一个用户故事需要多个微服务协作时，Agent 很难做好跨服务设计——因为它需要精确理解每个服务的边界和业务概念。

## 解决思路：三层策略

### 1. 统一上下文（工作区组织）
- 采用 monorepo，或"虚拟 monorepo"（把多个仓库 clone 到本地一起）
- 让 Agent 能在一个地方看到所有 schema、API 和代码

### 2. 分层文档
- 根目录放索引文件（AGENTS.md / CLAUDE.md），映射所有服务
- 每个服务有各自的文档，描述其限界上下文（DDD 的 bounded context）
- 渐进式加载：Agent 先看索引，再按需读取相关细节
- 优先用自动生成的规范（如 OpenAPI），而不是手写文档，避免文档过时

### 3. 验证循环
- 用 mock server 和契约测试（contract testing）做本地验证
- 消费者驱动的契约测试（Pact）记录服务间的真实交互
- Agent 无需部署整个系统，就能对照服务契约验证改动

## 关键成功要素
- 文档与代码保持同步
- 使用机器可读的规范（OpenAPI、Pact）
- 把契约测试当作"活文档（living documentation）"

## 参考
- Anthropic 的上下文工程（context engineering）指南
- 契约测试框架 Pact
