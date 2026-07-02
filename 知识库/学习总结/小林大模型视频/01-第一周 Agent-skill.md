## AI技能的框架性思考 & 决策力（如何用特定AI技能解决特定问题）

#### 一、什么是Skill
**定义**：Skill是基于文件系统、可复用的资源，给Claude提供某个领域的专业知识（工作流、上下文、最佳实践），把"通用型 agent"变成"专家"。它和 prompt 的区别：prompt 是一次性的对话级指令，Skill 是**按需加载、一次创建到处自动复用**
skill = 提示词 + 工具脚本 + 渐进式披露
#### 二、Skill由哪些组成
SKILL.md + scripts + reference + assets
- SKILL 功能说明以及什么时候用，YMAL格式： name + description
- scripts 存放可执行脚本
- reference 存放规范说明、参考资料
- assets 存放物料、原材料
#### 三、为什么MCP相比Skill占用的上下文更多
- MCP所有的工具和工具说明会在每一轮的对话中加入到对话上下文中，**多个MCP的所有工具都会一次性给大模型吗？**
- 工具凌乱，大模型不清楚调用工具的顺序、组合方式、使用场景（待确认，我认为比较模凌两可）
#### 四、Skill的优势
- **上下文可控**：渐进式披露机制
- **把Know- how集成到Agent**：沉淀机制、规则、操作步骤到文档，无需每次都输入给agent
- **人人可搭建**：以Markdown格式方便写入
- **具备可执行脚本**：调用脚本的时机是可控的，脚本也会按需使用加载的 
#### 五、Agent SDK 如何实现使用skill
- skill按照约定的YMAL格式写明白 name + description
- 每次和大模型交互时在系统提示词中加入：“本地可用的skill有XXX，他们的name、description、filePath”，并赋予大模型查看文件、写入文件、搜索文件的工具。连同工具一起发送给大模型
- 由大模型自行判断当前功能适合用哪些skill，并且继续调用工具获取skill的详细内容，当然这个流程都在整个loop中
- loop原理讲解：
	- 系统提示词是固定的，身份信息  + skill描述 
	- TOOLS 和 message（多轮对话内容、工具调用结果）通过tools和message传入
	- 整体设置30次循环调用，超过30次或模型没有调用工具则判定循环结束
	- 模型给出的工具调用、工具调用执行结果均需完整添加到message数组中
	- 注意设定角色为role。 messages.append({"role": "assistant", "content": response.content})


 