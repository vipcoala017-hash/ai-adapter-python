# Python AI Adapter

独立的本地 AI 适配工具。

## 规则

- 配置文件在 `tool/ai_adapter.toml`
- `PRD.toml` 在 `project/` 根目录
- provider 使用 `[providers.<name>]` 扩展
- `ai.ai_provider = "<name>"` 时，会使用 `providers.<name>` 的 CLI 模板
- `agent.model = { <name> = "" }` 与 provider 名称对应

`PRD.toml` 缺失时，工具会先创建模板并退出，提示你补内容后重试。

## 运行示例

### PowerShell

```powershell
cd D:\workspace\solo-noui-nogit-harness-prompt\ai-adapter-python\tool\src
python -m ai_adapter_tool status --config ..\ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool dry-run --config ..\ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool run --config ..\ai_adapter.toml --agent general-senior-dev-agent
```

### Bash

```bash
cd /d/workspace/solo-noui-nogit-harness-prompt/ai-adapter-python/tool/src
python -m ai_adapter_tool status --config ../ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool dry-run --config ../ai_adapter.toml --agent general-senior-dev-agent
python -m ai_adapter_tool run --config ../ai_adapter.toml --agent general-senior-dev-agent
```

### Python

```python
import os
import sys

cwd = r"D:\workspace\solo-noui-nogit-harness-prompt\ai-adapter-python\tool\src"
config = r"..\ai_adapter.toml"
agent = "general-senior-dev-agent"

os.chdir(cwd)
sys.path.insert(0, cwd)

from ai_adapter_tool import execute

execute(["status", "--config", config, "--agent", agent])
execute(["dry-run", "--config", config, "--agent", agent])
execute(["run", "--config", config, "--agent", agent])
```
