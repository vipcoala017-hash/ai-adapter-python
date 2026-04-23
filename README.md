# Python AI Adapter

独立的本地 AI 适配工具。

## 规则

- 配置文件在 `tool/ai_adapter.toml`
- 默认三层目录是 `tool/`、`ai_config/`、`project/`
- `ai_adapter.toml` 提供默认值；必要路径都可以通过命令行 `--xxx` 直接覆盖
- `project_dir` 默认指向目标项目目录
- `ai_config.dir` 默认指向 agent/rules/provider 配置目录
- `ai_config.cleanup_generated_artifacts` 默认 `true`，运行完成后会自动删除 `logs/`、`session-state/` 和 `config.json`
- agent 文档中的规则路径直接写成相对于 `ai_config.dir` 根目录的位置，不生成临时 ai_config，也不做路径替换
- `PRD` 通过 `ai_adapter.toml` 中的 `[prd].default` + `[prd.refs]` 映射到具体文件
- provider 使用 `[providers.<name>]` 扩展
- `ai.ai_provider = "<name>"` 时，会使用 `providers.<name>` 的 CLI 模板
- `agent.model = { <name> = "" }` 与 provider 名称对应
- 每次 `run` 执行完成后，工具会自动清理 `ai_config.dir` 下的 `logs/`、`session-state/` 和 `config.json`

## 语言约定

- 面向用户的输出、仓库文档和 PR 说明使用中文。
- 代码内注释使用英文，尤其是契约、参数、返回值、错误行为、并发与副作用说明。
- 若规则与注释出现表面冲突，以 [ai_config/rules/core_principles.md](ai_config/rules/core_principles.md) 中的优先级说明为准。

默认 `PRD` 文件缺失时，工具会先创建模板并退出，提示你补内容后重试。

## 配置示例

```toml
[common]
project_dir = "../project"
runtime_dir = "runtime"

[ai_config]
dir = "../ai_config"

[prd]
default = "default"

[prd.refs]
default = "PRD.toml"
demo = "prds/demo.toml"
```

命令行覆盖优先级高于 `ai_adapter.toml` 默认值：

- `--project-dir`：覆盖 `project_dir`
- `--ai-config-dir`：覆盖 `ai_config.dir`
- `--prd-name`：覆盖 `[prd].default`，按 `[prd.refs]` 查找具体文件
- `--prd-path`：直接指定 PRD 文件路径，优先级高于 `--prd-name`
- `--cleanup-ai-config-artifacts` / `--no-cleanup-ai-config-artifacts`：控制 run 完成后是否删除 `logs/`、`session-state/` 和 `config.json`

## 运行示例

### PowerShell

```powershell
cd D:\workspace\solo-noui-nogit-harness-prompt\ai-adapter-python\tool\src
python -m ai_adapter_tool status --config ..\ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool dry-run --config ..\ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool run --config ..\ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool status --config ..\ai_adapter.toml --agent general-senior-dev-agent --project-dir D:\workspace\my-project --ai-config-dir D:\workspace\my-ai-config --prd-name demo
```

### Bash

```bash
cd /d/workspace/solo-noui-nogit-harness-prompt/ai-adapter-python/tool/src
python -m ai_adapter_tool status --config ../ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool dry-run --config ../ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool run --config ../ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool status --config ../ai_adapter.toml --agent general-senior-dev-agent --project-dir /workspace/my-project --ai-config-dir /workspace/my-ai-config --prd-name demo
python -m ai_adapter_tool status --config ../ai_adapter.toml --agent general-senior-dev-agent --project-dir /workspace/my-project --prd-path /workspace/my-project/prds/demo.toml
```

### Python

```python
import os
import sys

cwd = r"D:\workspace\solo-noui-nogit-harness-prompt\ai-adapter-python\tool\src"
config = r"..\ai_adapter.toml"
agent = "general-senior-dev-agent"
project_dir = r"D:\workspace\my-project"
ai_config_dir = r"D:\workspace\my-ai-config"
prd_name = "demo"

os.chdir(cwd)
sys.path.insert(0, cwd)

from ai_adapter_tool import execute

execute(["status", "--config", config, "--agent", agent])
execute(["dry-run", "--config", config, "--agent", agent])
execute(["run", "--config", config, "--agent", agent])
execute([
	"status",
	"--config", config,
	"--agent", agent,
	"--project-dir", project_dir,
	"--ai-config-dir", ai_config_dir,
	"--prd-name", prd_name,
])
```
