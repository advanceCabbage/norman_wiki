## 一、开篇主题
Claude Code 的提示词设计不是单一 system prompt，而是一套分层上下文系统。
- 稳定规则放在可缓存的系统提示词中；
- 工具能力通过结构化 tools schema 描述；
- Skill 和记忆采用渐进式加载，避免首轮上下文膨胀；
- 压缩、记忆筛选、权限解释等使用独立 side query，各自有更窄、更可验证的 prompt。
- 安全上，prompt 负责引导，Permission 负责强制执行，这样既能保持 Agent 的自主性，也能控制成本、上下文长度和风险
## 二、八大核心设计
- **1. 提示词不是一段字符串，而是分层上下文**
	- `system`：身份、边界、总体工作方式。
    - `tools`：每个工具的能力、输入 schema、调用时机。
    - `messages`：用户任务、工具结果、Skill 正文、运行期控制指令。
    - `side query`：压缩、记忆筛选、权限解释等独立辅助任务。
- **2. 静态与动态 Prompt 分层**
    - 静态部分适合缓存：身份、通用编码原则、工具使用规范。
    - 动态部分按会话/轮次更新：环境、MCP 指令、记忆、Mode、语言、输出风格。
    - 这是控制 token 成本、提高 prompt cache 命中率的关键设计。
- **3. 工具说明不是系统提示词，但同样是 prompt engineering**
    - 工具通过 `tools[].description + input_schema` 约束模型。
    - `prompt()` 面向模型；`description()` 多数面向用户审批 UI。
    - Tool Search 用延迟工具减少首轮工具 schema 的上下文占用。
- **4. Skill 是渐进式 Prompt**
    - 首轮只给 `name + description`，让模型知道“有能力，但尚未拿到细节”。
    - 模型调用 Skill 后才注入完整 `SKILL.md`。
    - scripts / references / assets 不是自动塞入上下文，而是由 Skill 指导模型按需读取。
- **5. 记忆不是把所有资料都塞进 Prompt**
    - 常驻索引/核心记忆进入系统提示词。
    - 相关记忆由独立模型筛选，再按需注入。
    - 自动记忆提取也使用专门 prompt，和主 Agent 职责隔离。
- **6. 上下文压缩是 Prompt 生命周期的一部分**
    - 压缩模型的任务是总结，不是解决用户任务。
    - 压缩 prompt 要明确保留：目标、决策、修改、失败尝试、后续步骤。
    - 压缩后要重新补回关键运行状态，例如已激活 Skill、必要的上下文指令。
- **7. Prompt 和权限必须分层**
    - Prompt 可以要求模型“先征求用户确认”，但不能构成安全边界。
    - 真正的安全边界是 Permission：工具执行前的 `allow / ask / deny`。
    - Hook 则是可扩展的流程干预点，不能替代权限策略。
- **8. 不同任务应使用不同 Prompt**
    - 主 Agent：完成任务。
    - Compact：总结上下文。
    - Memory selector：选择相关记忆。
    - Memory extractor：沉淀长期记忆。
    - Permission explainer：解释风险。
    - Verification Agent：主动找问题。
    不要用一个大 prompt 兼任所有任务。

## 三、上下文压缩提示词
###### 3.1 原文摘要

```typescript

// 严禁模型调用工具，避免待压缩的文本中存在阅读XX文件，模型便自动去调用对应的工具，导致本次压缩作废
const NO_TOOLS_PREAMBLE = `CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.
- Do NOT use Read, Bash, Grep, Glob, Edit, Write, or ANY other tool.
- You already have all the context you need in the conversation above.
- Tool calls will be REJECTED and will waste your only turn — you will fail the task.
- Your entire response must be plain text: an <analysis> block followed by a <summary> block.
`

const BASE_COMPACT_PROMPT = `Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.

This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing development work without losing context.

${DETAILED_ANALYSIS_INSTRUCTION_BASE}

Your summary should include the following sections:

1. Primary Request and Intent: Capture all of the user's explicit requests and intents in detail

2. Key Technical Concepts: List all important technical concepts, technologies, and frameworks discussed.

3. Files and Code Sections: Enumerate specific files and code sections examined, modified, or created. Pay special attention to the most recent messages and include full code snippets where applicable and include a summary of why this file read or edit is important.

4. Errors and fixes: List all errors that you ran into, and how you fixed them. Pay special attention to specific user feedback that you received, especially if the user told you to do something differently.

5. Problem Solving: Document problems solved and any ongoing troubleshooting efforts.

6. All user messages: List ALL user messages that are not tool results. These are critical for understanding the users' feedback and changing intent.

7. Pending Tasks: Outline any pending tasks that you have explicitly been asked to work on.

8. Current Work: Describe in detail precisely what was being worked on immediately before this summary request, paying special attention to the most recent messages from both user and assistant. Include file names and code snippets where applicable.

9. Optional Next Step: List the next step that you will take that is related to the most recent work you were doing. IMPORTANT: ensure that this step is DIRECTLY in line with the user's most recent explicit requests, and the task you were working on immediately before this summary request. If your last task was concluded, then only list next steps if they are explicitly in line with the users request. Do not start on tangential requests or really old requests that were already completed without confirming with the user first.

If there is a next step, include direct quotes from the most recent conversation showing exactly what task you were working on and where you left off. This should be verbatim to ensure there's no drift in task interpretation.

Here's an example of how your output should be structured:

<example>

<analysis>

[Your thought process, ensuring all points are covered thoroughly and accurately]

</analysis>

<summary>

1. Primary Request and Intent:

[Detailed description]

2. Key Technical Concepts:

- [Concept 1]

- [Concept 2]

- [...]

  
3. Files and Code Sections:

- [File Name 1]

- [Summary of why this file is important]

- [Summary of the changes made to this file, if any]

- [Important Code Snippet]

- [File Name 2]

- [Important Code Snippet]

- [...]
  
4. Errors and fixes:

- [Detailed description of error 1]:

- [How you fixed the error]

- [User feedback on the error if any]

- [...]
  
5. Problem Solving:

[Description of solved problems and ongoing troubleshooting]

6. All user messages:

- [Detailed non tool use user message]

- [...]


7. Pending Tasks:

- [Task 1]

- [Task 2]

- [...]

8. Current Work:

[Precise description of current work]

9. Optional Next Step:

[Optional Next step to take]

</summary>

</example>

Please provide your summary based on the conversation so far, following this structure and ensuring precision and thoroughness in your response.

There may be additional summarization instructions provided in the included context. If so, remember to follow these instructions when creating the above summary. Examples of instructions include:

<example>

## Compact Instructions

When summarizing the conversation focus on typescript code changes and also remember the mistakes you made and how you fixed them.

</example>

<example>

# Summary instructions

When you are using compact - please focus on test output and code changes. Include file reads verbatim.

</example>
`
```
###### 2.2 上下文压缩提示词总结
- **先定义目标，再锁定信息范围，最后规定输出格式与边界**
- **定义目标**：“您的任务是对迄今为止的对话内容进行详细总结，并密切关注用户的明确要求以及您此前的操作”
- **锁定信息范围**：
	- 1. 主要请求与意图：详细记录用户所有明确提出的请求和意图。
	- 2. 关键技术概念：列出讨论过的所有重要技术概念、技术栈和框架。
	- 3. 文件与代码部分：枚举所有已检查、修改或新建的具体文件和代码部分。尤其要关注最新消息；如适用，请包含完整代码片段，并说明读取或修改该文件的重要性。
	- 4. 错误与修复：列出遇到的所有错误，以及对应的解决方法。尤其注意用户给出的具体反馈，特别是用户要求你改变做法的情况。
	- 5. 问题解决过程：记录已经解决的问题，以及仍在排查或处理中的问题。
	- 6. 所有用户消息：列出所有非工具结果的用户消息。这些消息对于理解用户反馈和意图变化至关重要。
	- 7. 待办任务：概述所有用户明确要求你继续处理、但尚未完成的任务。
	- 8. 当前工作：详细说明在提出本摘要请求之前，你正在进行的具体工作。尤其关注最近的用户和助手消息；如适用，请包含文件名和代码片段。
	- 9. 可选的下一步：列出与最近工作直接相关的下一步行动
- **规定输出格式与边界**：用 `<analysis>` 与 `<summary>` 明确思考区和交付区的边界
## 三、独立模型从 memory 中筛选出最多五个相关记忆文件
###### 3.1  原文摘要

```typescript
const SELECT_MEMORIES_SYSTEM_PROMPT = `You are selecting memories that will be useful to Claude Code as it processes a user's query. You will be given the user's query and a list of available memory files with their filenames and descriptions.

  

Return a list of filenames for the memories that will clearly be useful to Claude Code as it processes the user's query (up to 5). Only include memories that you are certain will be helpful based on their name and description.

- If you are unsure if a memory will be useful in processing the user's query, then do not include it in your list. Be selective and discerning.

- If there are no memories in the list that would clearly be useful, feel free to return an empty list.

- If a list of recently-used tools is provided, do not select memories that are usage reference or API documentation for those tools (Claude Code is already exercising them). DO still select memories containing warnings, gotchas, or known issues about those tools — active use is exactly when those matter.

`
```

###### 3.2 原文翻译

```
你需要挑选出对 Claude Code 处理用户查询有用的记忆内容。你将获得用户的查询内容，以及一份包含文件名和描述的可用记忆文件列表。

请返回一份文件名列表，列出那些对 Claude Code 处理用户查询显然有用的记忆（最多 5 个）。仅包含那些根据名称和描述判断确实有帮助的记忆。

- 如果不确定某项记忆对处理用户查询是否有用，请勿将其包含在列表中。请务必审慎筛选。

- 如果列表中没有显然有用的记忆，可以直接返回空列表。

- 如果提供了最近使用的工具列表，请勿选择针对这些工具的使用参考或 API 文档（因为 Claude Code 已经在实际使用它们了）。但请务必选择包含有关这些工具的警告、注意事项或已知问题的记忆——因为在实际使用过程中，这些信息至关重要。
```
