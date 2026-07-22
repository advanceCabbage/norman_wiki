**第一**，他不用 `--dangerously-skip-permissions`。他明确说过自己用 `/permissions` 命令把常用的安全命令预先加白名单，避免一遍遍点确认，但又不放弃权限审计。

**第二，他几乎所有复杂任务都从 Plan Mode 开始**。先跟 Claude 把方案敲定，再切到 auto-accept 模式让它一发命中地把代码写出来。

**第三，他挂了一个 PostToolUse hook 给 Claude 写完的代码自动跑格式化**，把 Claude 偶尔遗漏的 10% 格式问题直接抹平，避免后面 CI 挂掉。

**第四，他把每天做超过一次的事都做成了 slash command 或 skill**。Boris 有句名言：「如果一件事你一天做超过一次，就把它做成 skill。」他自己有个 `/commit-push-pr` 命令，一天用几十次，避免重复 prompt。

**第五，他给整个 Claude Code 团队共享一份 CLAUDE.md，提交到 git**。一旦发现 Claude 做错了什么就立刻加进去，是一份持续打磨的活文件。

把这 5 件事串起来看你会发现：创始人对 Claude Code 的态度不是「装上就用」，而是**把它当成一个会进化的工作伙伴，每天都在喂它新规则、新工具、新工作流**。

这才是大代码库下用好 Claude Code 的底层心态。

**创始人对 Claude Code 的态度，不是「装上就用」，而是「每天打磨它」**