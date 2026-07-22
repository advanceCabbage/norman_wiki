## 一、开篇点题
Claude code在代码检索方面并没有使用RAG，而是使用Grep、Glob加Read三件套工具，外加上派子agent探索的设计
- 第一，代码场景下 RAG 有切片破坏结构、向量近似不准、索引滞后等本质问题
- 第二，Claude Code 用 Grep 加 Glob 加 Read 三件套加上派子 agent 探索的设计，本质上是把检索决策权还给 LLM 自己，配合多轮迭代循环实现精准定位
- 第三，更深层是 Anthropic 信任 LLM 的能力，押注模型会越来越强，所以选择「不替模型做决定」的设计哲学

RAG 派的潜台词是：**LLM 不够强，所以我们要用工程手段帮它把材料准备好**。chunking、embedding、向量召回，本质都是「替模型做决定」。

Claude Code 派的潜台词是：**LLM 已经足够强，工程的角色是给它准备好工具，把决策权还给它**。grep 不替模型做任何决定，它只是个工具。用还是不用、什么时候用、怎么用，全是模型说了算。
## 二、使用RAG检索代码的痛点
- 第一，**冷启动**。grep 是毫秒级响应，开箱即用；RAG 要先建索引，分钟级冷启动，劝退一半用户。

- 第二，**实时性**。grep 每次现读磁盘最新版本；RAG 索引会滞后，文件改了得重建。

- 第三，**精确性**。grep 是确定性的字符正则匹配，要找 `getUserById` 就只有它；RAG 是向量近似匹配，会把一堆相似函数糊在一起。

- 第四，**Token 经济**。grep 加 Read 按需读取，模型只看真正需要的几行；RAG 一上来就要给整个代码库做 embedding，存储和计算成本都不小。

- 第五，**可解释性**。grep 每一步检索过程都对用户透明可审计；RAG 的 Top-K 召回是黑盒，出 bug 没法 debug。

- 第六，**决策权**。grep 让 LLM 自己决定每一轮搜什么、读什么，多轮迭代逐步逼近答案；RAG 是一次性把材料丢给模型，模型只能将错就错
## 三、Claude Code代码检索思路

**不预处理、不建库、不算向量，每次需要代码就实时去现场查**。工具就给三个：
- **Glob**：按文件名 pattern 找文件（对应你的 `find`）
- **Grep**：按内容关键字找代码（对应你的 `grep -r`）
- **Read**：按需读文件内容（对应你的 `cat` 和编辑器跳转）
本质上是把「找代码」的决策权还给了 LLM。你不需要提前猜模型会问什么，也不需要给它装个「智能召回引擎」，模型自己想搜什么就搜什么，搜完看一眼结果，再决定下一步

#### 3.1 Grep工具
**功能**：按文件内容的正则表达式找匹配的文件,支持输出三种模式内容：**content 模式**、**files_with_matches 模式**（文件列表按修改时间倒序排列）、**count 模式**（发现匹配文件的数量）

**优势**：
- **权限统一管控**：Claude  Code单独把grep封装为工具，避免CC调用Bash等工具，更加收紧工具权限以及模型正确使用工具
- **输出格式可控**：假设使用Bash工具，输出内容是一段文本，提供Grep工具可以约定工具输出内容的格式。例如：结构化输出行号。
- **性能**：Grep底层使用ripgrep，使用Rust实现。具备：多线程并行、自动尊从.gitignore，性能比传统 grep高很多
- **最多输出 250个结果项**：可以支持分页获取更多结果项
- **开放式、多轮搜索使用 Agent工具**：工具定义中有提示大模型，当在开发式、多轮迭代的搜索请创建子agent

```
A powerful search tool built on ripgrep  
- ALWAYS use Grep for search tasks. NEVER invoke `grep` or `rg` as a Bash   
  command. The Grep tool has been optimized for correct permissions and access.  
- Output modes: "content" shows matching lines, "files_with_matches" shows   
  only file paths (default), "count" shows match counts  
- Use Agent tool for open-ended searches requiring multiple rounds

基于 ripgrep 打造的强力搜索工具  
- 搜索任务请永远使用 Grep。绝对不要用 Bash 命令调用 `grep` 或 `rg`。  
  Grep 工具已经针对权限和访问做过优化。  
- 输出模式："content" 返回匹配的具体行，"files_with_matches" 只返回  
  文件路径（默认），"count" 只返回匹配数量  
- 开放式、需要多轮迭代的搜索，请用 Agent 工具
```

#### 3.2 Glob 
**功能**：按文件路径或名称模式查找文件，支持输入正则表达式或路径，输出文件路径列表

**优势**：
- **第一，结果按修改时间倒序排列**。也就是说，最近改过的文件排在前面。为啥这样？因为大部分时候，「最近改过的」就是「跟当前任务最相关的」。这是个很朴素但很有效的启发式规则。
- **第二，结果有 100 文件硬上限。** 超出会截断，避免输出爆炸把上下文塞满。模型如果还想看更多，可以收紧 pattern 再搜一次

#### 3.3 Read
**功能**：读取文件内容，输入文件绝对路径，输出文件内容
**优势**：**默认只读 2000行，超出会截断**，每次读取最新内容，**不缓存、不索引、不预处理**，这套设计的核心思想就一句话：**模型应该按需读取，不要贪心**。

**工具定义**：
```json
By default, it reads up to 2000 lines starting from the beginning of the file.  
When you already know which part of the file you need, only read that part.  
This can be important for larger files.

默认从文件开头读取，最多读 2000 行。  
如果你已经知道需要文件的哪一部分，就只读那一部分。  
对大文件来说，这一点特别重要。
```

## 四、当三件套不够用：派子 agent 去探索

**使用场景**：对于大型项目或整个搜索过程可能调用 十几个工具调用，大量文件检索内容对主agent来说是严重的上下文污染

**子agent执行的流程**大致为：
第一，主 agent 通过 Agent 工具派子 agent
第二，子 agent 拿到一个精简的工具池。通常是只读工具：Grep、Glob、Read、Bash（只读命令）
第三，子 agent 在自己的上下文里多轮迭代
第四，子 agent 完成后，只把最终结论返回给主 agent

**Claude code在大型代码检索上的分层设计**：
- **底层**：Grep / Glob / Read 三件套，处理简单定向检索
- **中层**：派 Explore 子 agent，处理开放式探索和上下文隔离
- **上层**：主 agent 编排整体任务

## 五、LSP

Claude code默认没有安装LSP插件，需要手动安装LSP插件。以TS举例：
- 第一步：通过/plugin 安装typescript-lsp插件
- 第二步：全局安装 Typescript 语言服务器，npm install -g typescript-language-server typescript
- 第三步：Claude code会在本机启动语言服务器的进程

在以下场景会Claude code会默认调用LSP的相关工具。
LSP 用于"已知符号、要精确定位"的场景（仅对配置了语言服务器的文件类型有效，这里是 TypeScript/JS）：
- 已经知道某个函数/类型/变量名，想找它的定义、所有引用、调用者/被调用者
- 想要类型信息、hover 文档
- 需要跨文件的语义级导航（比 grep 文本匹配更准确，比如能区分同名但不同作用域的符号）

Grep/Glob 用于"文本/文件模式匹配"的场景，我仍然会大量使用：
- 探索性搜索："哪里用到了 auto-update 这个功能"这类关键词/字符串搜索，还不知道具体符号名或位置
- 跨语言、跨文件类型：仓库里有 Swift（iOS）、Kotlin（Android）、Markdown、YAML、JSON 配置等，LSP 只覆盖 TS/JS
- 按文件名/路径查找文件（Glob），比如找所有 *.test.ts
- 搜索非代码符号的内容：注释、字符串字面量、日志文本、docs
- **LSP 操作本身需要精确的 line/character 位置作为输入 —— 所以常见流程是先用 Grep 定位到大致位置，再用 LSP 做 findReferences/goToDefinition 这类精确跟进，而不是单独用 LSP 从零开始搜索**

