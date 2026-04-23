# 快速使用

## 必要配置

1. `tool\ai_adapter.toml`
2. `ai_config\`
3. `project` 下的 PRD 文件，例如 `PRD.toml`

## 调用示例

1. 进入仓库根目录
2. 运行：

```powershell
python -m ai_adapter_tool run --config tool\ai_adapter.toml --agent general-senior-dev-agent
```

# 配置说明

`tool\ai_adapter.toml` 是主配置文件，实际会读取以下区块。

## `[common]`

负责仓库级路径和运行目录。

| 字段 | 说明 |
| --- | --- |
| `project_dir` | 要操作的项目根目录。可写相对路径或绝对路径，示例值为 `D:\ai-adapter-python`。 |
| `runtime_dir` | 运行时输出目录名，必须是相对路径。程序会在 `project_dir` 下生成 `runtime\ai-runs\...`。 |

## `[ai_config]`

负责 AI 配置目录及其运行后清理策略。

| 字段 | 说明 |
| --- | --- |
| `dir` | `ai_config` 目录路径。用于查找 `rules\`、`agents\`、`config.json` 等文件。 |
| `cleanup_generated_artifacts` | 是否在 `run` 完成后删除 `ai_config` 下的临时产物，包括 `logs`、`session-state` 和 `config.json`。 |

## `[prd]`

负责本次任务的 PRD 选择。

| 字段 | 说明 |
| --- | --- |
| `default` | 默认 PRD 别名。未传 `--prd-name` 时使用它。 |
| `refs` | PRD 别名到文件路径的映射。当前示例中 `default = "PRD.toml"`。 |

## `[ai]`

负责 AI 调用方式。

| 字段 | 说明 |
| --- | --- |
| `ai_provider` | 当前启用的 provider 名称，必须能在 `[providers.<name>]` 中找到对应模板。 |
| `default_agent` | 未传 `--agent` 时使用的 agent 名称。 |
| `prompt_mode` | 提示词传递方式，只支持 `stdin` 或 `arg`。 |
| `launch_mode` | 子进程启动方式，只支持 `direct`、`powershell` 或 `bash`。 |
| `timeout_seconds` | 单次调用超时时间，单位秒。 |
| `yolo` | 是否向 provider CLI 追加 `--yolo`。 |

## `[providers.*]`

每个 provider 定义一条 CLI 模板。

| 字段 | 说明 |
| --- | --- |
| `cli` | 实际启动命令模板。支持占位符 `{{agent.name}}`、`{{agent.model.<provider>}}`、`{{ai_config_dir}}`、`{{project_dir}}`、`{{prd_path}}`、`{{agent_file}}`、`{{yolo:--yolo}}`。 |

当前示例包含：

| provider | 模板用途 |
| --- | --- |
| `codex` | 调用 `codex exec`。 |
| `copilot` | 调用 `copilot --agent ...`。 |
| `claude` | 调用 `claude --model ...`。 |

## `[agents.*]`

每个 agent 定义名称和模型映射。

| 字段 | 说明 |
| --- | --- |
| `name` | agent 的实际名称。必须与 `ai_config\agents\*.md` 文件名对应。 |
| `model` | 各 provider 对应的模型名映射，例如 `codex`、`copilot`、`claude`。 |

## `PRD.toml`

`PRD.toml` 描述本次 PR 的目标。

| 字段 | 说明 |
| --- | --- |
| `title` | 任务标题，会进入运行时 prompt。 |
| `doc` | PRD 说明文档路径。可写相对路径或绝对路径，但最终必须落在 `project_dir` 内。 |
| `level` | 任务级别，默认是 `task`。 |

# 命令行覆盖选项

命令行参数的优先级高于配置文件。

## 通用选项

| 参数 | 说明 |
| --- | --- |
| `--config` | 指定 `ai_adapter.toml` 路径；也可通过环境变量 `AI_ADAPTER_CONFIG` 提供。 |
| `--agent` | 指定本次使用的 agent，优先于 `[ai].default_agent`。 |
| `--project-dir` | 覆盖 `[common].project_dir`。 |
| `--ai-config-dir` | 覆盖 `[ai_config].dir`。 |

## PRD 覆盖选项

| 参数 | 说明 |
| --- | --- |
| `--prd-name` | 按别名选择 PRD，会从 `[prd.refs]` 中查找。 |
| `--prd-path` | 直接指定 PRD 文件路径，优先级高于 `--prd-name`。 |

## 清理选项

| 参数 | 说明 |
| --- | --- |
| `--cleanup-ai-config-artifacts` | 运行结束后删除 `ai_config` 的临时产物。 |
| `--no-cleanup-ai-config-artifacts` | 运行结束后保留 `ai_config` 的临时产物。 |

## 规则说明

1. `--prd-path` 优先级最高，直接覆盖 PRD 文件位置。
2. `--prd-name` 只负责从 `[prd.refs]` 里选别名，不直接写文件路径。
3. 路径参数在 Windows 上建议使用反斜杠，带空格时请加引号。
4. `--project-dir` 和 `--ai-config-dir` 都会影响相对路径解析结果。

# 运行示例

PowerShell:

```powershell
cd D:\ai-adapter-python\tool\src
python -m ai_adapter_tool run --config ..\ai_adapter.toml --agent general-senior-dev-agent
```

Bash:

```bash
cd /d/ai-adapter-python/tool/src
python -m ai_adapter_tool run --config ../ai_adapter.toml --agent general-senior-dev-agent
```

Python:

```python
from ai_adapter_tool import execute
execute(['run', '--config', 'tool/ai_adapter.toml', '--agent', 'general-senior-dev-agent'])
```

更多细节请参阅 `ai_config` 目录下的 `rules\` 文档以及 `tool\ai_adapter.toml`。
