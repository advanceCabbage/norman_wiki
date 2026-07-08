## 一、Serena 是什么？

**Serena** 是一个基于 LSP 协议的**下一代 AI 编程助手平台**，专为智能代码分析、理解和编辑而设计。它将 LSP 的语言服务器能力与现代 AI 技术深度融合，为开发者提供了强大的代码操作工具集。

更多可见：[LSP与Serena](https://km.sankuai.com/collabpage/2716158192?kmId=2716158192&linkType=KM)

## 二、Serena 源码分析

#### 2.1 **serena** - 核心代理模块

- **SerenaAgent**: 主要的代理类，负责协调所有工具和服务
    
- **工具系统**: 包含 50+个专业编程工具
    
- **MCP 服务器**: 实现 Model Context Protocol，与 Claude 等 LLM 集成
    
- **配置管理**: 支持项目级、模式级、上下文级配置
    

#### **2.2 solidlsp** - LSP 集成模块

- **SolidLanguageServer**: 语言服务器抽象基类
    
- **多语言支持**: Python、TypeScript、Java、Rust、C#、Go、PHP 等
    
- **符号分析**: 代码符号解析、引用查找、定义跳转
    
- **语言服务器管理**: 自动启动、通信、缓存管理
    

#### **2.3 interprompt** - 提示模板系统

- **多语言提示**: 支持不同编程语言的专业提示
    
- **模板引擎**: 基于 Jinja 2 的动态提示生成
    
- **上下文感知**: 根据项目和模式调整提示内容
    

#### 2.4 LSP 通信流程

- **语言服务器启动**：根据项目语言自动选择和启动对应的语言服务器
    
- **文档同步**：保持内存中的文档状态与语言服务器同步
    
- **符号查询**：通过 LSP 协议进行符号定义、引用、补全等查询
    
- **缓存管理**：智能缓存符号信息，提高查询性能
    
- **错误处理**：自动重启语言服务器，处理通信异常
    

## 三、核心原理

#### 3.1 文档符号解析完整流程
![[c671a21d-fd96-415a-a83d-4356ed0f17d9.png|288]]
#### 3.2 双重存储结构设计
![[8e98eaa8-416b-4388-9558-27079b918997.png]]
#### 3.3 查找引用流程
![[0979fdd8-8dfd-4161-81f8-c09329214979.png]]
## 四、为什么 LSP 能为 AI Agent 提供精确的代码理解能力？

1. **语义级别的代码理解**
    1. LSP 不仅仅是文本处理，而是基于编程语言的语法和语义规则进行深度分析
```
# 传统文本搜索：只能找到字符串匹配
grep -r "function_name" .

# LSP 符号查找：理解语义上下文
symbol_manager.find_by_name("ClassName.method_name")  # 精确定位到类的方法
```

- **跨文件依赖分析**
	- LSP 构建完整的项目依赖图，理解模块间的引用关系
```
ef find_referencing_symbols(self, name_path: str, relative_file_path: str) -> list[ReferenceInSymbol]:
    """
    AI Agent 可以通过此方法了解：
    1. 哪些函数调用了目标函数
    2. 哪些类继承了目标类
    3. 哪些模块导入了目标符号
    这为代码重构和影响分析提供了精确的信息
    """
    symbol_candidates = self.find_by_name(name_path, within_relative_path=relative_file_path)
    references = []
    
    for symbol in symbol_candidates:
        lsp_references = self._lang_server.request_referencing_symbols(
            symbol.location.relative_path,
            symbol.location.start_line,
            symbol.location.start_column,
            include_body=include_body
        )
        references.extend(lsp_references)
    
    return references
```

- **类型感知的智能操作**
    1. LSP 提供类型信息，使 AI Agent 能够进行类型安全的代码生成
```
# AI Agent 可以获取函数签名信息
hover_info = language_server.request_hover("file.py", line=10, column=5)
# 返回: {"contents": "def process_data(data: List[Dict[str, Any]]) -> DataFrame"}

# 基于类型信息生成正确的调用代码
completions = language_server.request_completions("file.py", line=15, column=10)
# 返回类型匹配的方法和属性建议
```

- **多语言统一接口**
    1. LSP 为不同编程语言提供统一的接口，使 AI Agent 能够跨语言工作
```
# 统一的符号查找接口，支持 12+ 种编程语言
def create(config: LanguageServerConfig, logger: LanguageServerLogger, repository_root_path: str):
    if config.code_language == Language.PYTHON:
        ls = PyrightServer(config, logger, repository_root_path)
    elif config.code_language == Language.JAVA:
        ls = EclipseJDTLS(config, logger, repository_root_path)
    elif config.code_language == Language.TYPESCRIPT:
        ls = TypeScriptLanguageServer(config, logger, repository_root_path)
    # ... 其他语言
    
    # 所有语言服务器都提供相同的接口
    return ls  # 统一的 SolidLanguageServer 接口
```
