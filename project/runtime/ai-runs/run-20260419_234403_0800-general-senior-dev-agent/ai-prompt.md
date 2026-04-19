# AI Adapter Task

Agent: `general-senior-dev-agent`

## PRD

# 计算测试

PRD level: task
PRD doc: ./docs/计算需求.md

# 计算测试

验证一个最小任务：确认 `1 + 1 = 2`。

要求：

- 不扩展为数据库设计、程序实现或复杂验收流程。
- 输出应围绕这个最小计算需求。

## Output Requirements

- Follow the configured agent instructions if the CLI loads one.
- Keep outputs grounded in the PRD.
- If writing files, write only under the target_dir.
