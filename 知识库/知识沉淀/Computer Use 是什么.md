
> **一句话总结**：Computer Use 是 Anthropic 为 Claude 开发的能力，让 AI 能像人一样操作电脑——看屏幕截图、移动鼠标、点击按钮、输入文字，从而完成复杂的计算机任务。

---

## 核心概念

Computer use 的本质是把「截图 + 鼠标键盘」包装成一个普通的 tool：模型本身碰不到电脑，它只是看着截图输出 `{"action": "left_click", "coordinate": [512, 384]}` 这样的 JSON，真正执行的是 harness 里的本地代码（xdotool / CGEvent / CDP），执行完再截一张图作为 image content block 塞回 `tool_result`，循环往复 —— 所以它就是个标准 agentic loop，唯一特殊之处是 observation 变成了图像、模型需要具备从像素判断点击位置的 visual grounding 能力（这是 Claude 3.5 Sonnet new 起专门训练的）。

工程上真正的关键不在这个循环，而在**接口选择**：像素路径每步上千 token 且定位不可靠，所以能用 shell 就用 shell（Claude Code、Codex 的主路径），GUI 场景优先用 accessibility tree / DOM 拿到元素引用直接点，实在拿不到结构（canvas、游戏、自绘控件）才降级到像素；配套还得处理截图缩放与坐标回映射、截图历史裁剪防止上下文爆炸，以及最重要的一条安全边界 —— 屏幕上看到的一切都是数据而非指令，否则网页里一句话就能劫持你的 agent


Computer Use 是一种「工具调用」能力，赋予 Claude 以下操作权限：

| 操作类型      | 说明              |
| --------- | --------------- |
| 截图        | 获取当前屏幕状态，作为视觉输入 |
| 鼠标移动 / 点击 | 精准点击界面元素        |
| 键盘输入      | 输入文字、快捷键操作      |
| 滚动        | 页面滚动以查看更多内容     |

## 工作原理

```
用户下达任务
    ↓
Claude 截图分析当前屏幕
    ↓
决策：下一步要做什么操作
    ↓
执行操作（点击/输入等）
    ↓
再次截图，观察结果
    ↓
循环直到任务完成
```

## 典型使用场景

- 自动填写网页表单
- 操作桌面应用（Excel、PS 等）
- 自动化测试（替代部分 UI 测试）
- 数据采集（浏览网页并提取信息）
- 复杂工作流自动化

## 接入方式

通过 Anthropic API，指定支持 Computer Use 的模型（如 `claude-opus-4-6`），并提供 `computer_20250124` 工具：

```python
tools = [
    {
        "type": "computer_20250124",
        "name": "computer",
        "display_width_px": 1280,
        "display_height_px": 800,
    }
]
```

## 注意事项

- 仍处于 **beta 阶段**，复杂任务可能出错
- 操作速度比人慢（每步需截图分析）
- 安全边界：避免授权敏感账号操作
- 费用按 token 计算，截图消耗较多 token

## 与 RPA 的区别

| 维度 | 传统 RPA | Computer Use |
| --- | --- | --- |
| 规则定义 | 人工录制/编写 | AI 自主推理 |
| 适应变化 | 弱（界面变化即失效） | 强（视觉理解） |
| 上手难度 | 中 | 低（自然语言描述任务）|
| 稳定性 | 高 | 中（仍在进化）|
