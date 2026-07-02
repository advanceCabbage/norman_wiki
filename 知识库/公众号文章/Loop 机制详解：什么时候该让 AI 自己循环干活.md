# Loop 机制详解：什么时候该让 AI 自己循环干活

## 一、背景现状

AI进入大众视野多年，大多数人每天都在使用AI，但依然用着效率最低的方式：手动输入指令、等待结果、修改、再追问 ——全程纯手工操作。不是因为更快的方法太复杂，而是大家没有注意到，实际上更快的方法是循环（Loop），这也是全球顶尖AI工程师最关注的核心，本文将讲解Loop是什么、底层原理如何运作、何时值得使用以及何时是个陷阱，学习如何在Claude、Codex中创建一个基础的循环

## 二、什么是Loop？

Prompt是一条单一指令。而Loop是一个AI会持续努力直至达成的目标。它是一个递归式的目标：你设定一个目的，AI就会不断迭代，直到任务完成。
提示词给你一个答案，然后等你决定下一步做什么。而循环会自动运行完整的周期：
![[Pasted image 20260702202410.png]]`

- **探索** → 明确需要做什么
- **规划** → 决定如何实施
- **执行** → 开展工作
- **验证** → 对照目标进行检查
- **迭代** → 尚未达标？将结果反馈并重复流程
五个步骤中：执行、验证、迭代三个步骤承担了主要工作，而这也是大家使用循环时容易出错的地方。总结来说：**Prompt（提示词）是给 AI 一条指令。而 Loop（循环）则是给 AI 一项任务、一套判断任务何时完成的标准，以及一套何时该放弃的准则**。

## 三、你何时需要一个Loop

我认为以下四点全部成立时，才值得去构建一个循环，否则将其作为提示词输入即可，loop engineering 确实存在，但大多数人目前还不需要这种重量级的版本：

- **高频重复周期**：该任务至少每周重复一次。频率过低的话，配置成本就永远无法收回。一次性的任务，用一个高质量的提示词处理反而更好
- **具备可验证机制**：具备某种机制可以自动拒绝劣质输出。比如：测试、类型检查、构建程序、代码检查工具或者一条硬性规则。如果没有任何东西能帮你把关，这个循环只会原地空转
- **智能体能独立完成工作**：智能体能独立完成工作，无需人工介入
- **完成是客观事实，而非主观判断**：完成事项由统一的成功标准，而不是因人而异，仁者见仁、智者见智

## 四、Loop由五个部分组成

Loop概念最早是在软件领域兴起的，因为代码是世界上最容易验证的东西。测试要么通过，要么失败。这没法争辩，所以 AI 总是能知道它是否已经完成了任务。
在底层逻辑中，一个真正的循环是由五个构建模块组成的。Claude Code 和 Codex 现在都已经具备了这全部五个模块

- **自动化（心跳）**：在Claude code中，“/loop”能按时间间隔重复执行Prompt，“/goal”会保持绘画运行知道你设定的条件达成，Hooks在智能体的生命周期节点触发指令，而将其推送到corn job或GitHub Actions中，则能让你合上电脑后它依然持续运行
- **Skill**：将重复的指令、规则封装为一个文件，在Loop过程中由LLM按需读取、使用
- **Sub-agent**：在Loop中，实用的技巧是将“执行任务的智能体”与“负责审核的智能体”分开，确保不会出现自己实现自己评审的现象。配置更高算力的强模型进行评审能找出第一个智能体因盲目自信而忽略的问题，让你的执行者追求速度与性价比，而让你的审核者保持审慎与严苛。这种分离才是保证质量的关键。
- **渠道（连接器）**：连接器能让你的智能体在真实环境中付诸行动，而不仅仅是纸上谈兵。例如自动打开PR、关联工单
- **验证者**：自动拒绝不良产出的测试、类型检查或构建流程。这是决定循环反馈是在帮你还是在烧钱的唯一关键环节。其余的都是基础架构，唯有这部分才能让它真正发挥作用。
  将它们叠加在一起，你就得到了现在大团队大规模运行的模式：成群的智能体在同一个任务上循环，一次处理几十甚至上千个任务。一位工程师利用这种循环，仅用六天左右就将整个代码库从一种编程语言重写为另一种，而这项工作如果手工完成，则需要近一年时间。这是严肃软件开发方式的真正变革。但它也有一个演示中从未展示过的陷阱

## 五、Loop的成本

循环靠 token 运行，token 就是钱。真正的问题不是每步都有成本，而是成本会累加：每轮迭代，Agent 都要重新读一遍目标、代码、上次结果和报错信息，且内容只会越滚越长。所以运行十次的循环，花费不是十个提示词，而是十个体量递增的提示词。

"生成+检查"这类提质技巧也会让账单翻倍——因为多了一个模型来审阅同样的工作。经验法则：如果循环产出十个结果、你丢弃了六个，那你其实是在替它做审核；采纳率低于 50%，投入就超过了收益。

循环还会无声地失效，工程师 Geoffrey Huntley 称之为"拉尔夫·维古姆循环"（Ralph Wiggum loop）：智能体过早判定任务已完成、提前退出，循环却仍在运行、持续消耗资源，最终产出为零。

没有一道能让任务"失败"的硬性关卡，循环不会崩溃，只会悄悄持续收费。这就是为什么重量级版本（迭代上限、Token 预算、低成本模型、实时监控）更适合有预算和护栏机制的团队；没有这些配置也无妨，核心理念在低成本、无需复杂设置的情况下同样成立

#### 5.1 有效的构建顺序

如果你打算构建一个，顺序比工具更重要。那些能在生产环境中存活的循环（Loops）的构建者们，做法全如出一辙：
![[Pasted image 20260702202703.png]]
```
1. Get ONE manual run reliable first.
2. Turn that into a skill (save the instructions).
3. Wrap the skill in a loop (add the gate + stop condition).
4. THEN put it on a schedule.
```

跳过步骤，去调度那些尚未实现自动化的手动流程，正是循环在半夜崩溃的罪魁祸首。先验证一次，稳固它，然后再自动化

## 六、自己动手构建一个基础Loop

你不需要编码智能体也能感受到它是如何运作的。你现在就可以在任何 LLM 中手动运行一个简单的循环，只需一个提示词即可。诀窍在于同时给模型提供循环的三个部分：目标、严格的成功标准，以及一个强制它在停止前进行自我检查的协议

```*
▸ SELF-CHECKING LOOP  (paste into Claude or ChatGPT)
You will work in a loop until the task meets the bar.

TASK:
[describe exactly what you want produced]

SUCCESS CRITERIA (be strict, no soft passes):
- [criterion 1]
- [criterion 2]
- [criterion 3]

LOOP PROTOCOL, repeat every turn:
1. PLAN   - state the single next step.
2. DO     - produce or improve the work.
3. VERIFY - score the result 1-10 on each criterion.
            Be brutally honest. List exactly what is still weak.
4. DECIDE - if every criterion is 8+, print "FINAL" and stop.
            Otherwise print "ITERATING" and go again, fixing
            the weakest point first.

RULES:
- Never call it done until every criterion is 8 or higher.
- Each pass must fix the weakest score from the last VERIFY.
- Do not ask me questions. Make a sensible assumption, note it,
  and keep going.

Begin. Run the loop until FINAL.
```

看看会发生什么。模型先起草初稿，根据你的标准评估自己的作品，找出薄弱环节，然后不断重写，直到它真正达到要求，而不是直接把你看起来“差不多”的第一稿甩给你。这就是循环（loop）。你刚刚只用一段话就构建了一个循环。
