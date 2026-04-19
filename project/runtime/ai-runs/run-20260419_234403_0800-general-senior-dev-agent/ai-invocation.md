# AI CLI Invocation

- provider: `codex`
- strategy: `cli`
- cwd: `D:\workspace\ai-adapter-python\project`
- prompt: `D:\workspace\ai-adapter-python\project\runtime\ai-runs\run-20260419_234403_0800-general-senior-dev-agent\ai-prompt.md`
- prompt_mode: `stdin`
- launch_mode: `powershell`

## Logical CLI

```powershell
codex exec -c "model=gpt-5.4-mini" -c "model_instructions_file=.\.codex\agents\general-senior-dev-agent.md" --skip-git-repo-check --yolo
```

## Actual Subprocess Command

```powershell
powershell.exe -ExecutionPolicy Bypass -Command "$inputText = [Console]::In.ReadToEnd(); $inputText | codex exec -c 'model=gpt-5.4-mini' -c 'model_instructions_file=.\.codex\agents\general-senior-dev-agent.md' --skip-git-repo-check --yolo"
```

## Replay Command

```powershell
Get-Content -LiteralPath ai-prompt.md -Raw | codex exec -c "model=gpt-5.4-mini" -c "model_instructions_file=.\.codex\agents\general-senior-dev-agent.md" --skip-git-repo-check --yolo
```
