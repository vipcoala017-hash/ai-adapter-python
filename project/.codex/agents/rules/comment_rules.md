# 注释规则

## 通用原则

1. 必修使用英文注释
2. 注释描述契约、意图、边界和副作用，不重复代码执行细节。
3. 注释必须与代码签名和实现保持一致。参数、返回值、异常、副作用、线程或异步行为变化时，必须同步更新注释。
4. 注释必须便于检索。关键字段使用固定英文标签，例如 `Responsibility:`、`Side effects:`、`Error behavior:`。
5. 注释必须帮助 AI 判断“能不能改这里”“应该从哪里扩展”“风险在哪里”。

## 绝对禁止

1. 禁止注释与代码逻辑矛盾。
2. 禁止不写契约、约束、副作用和错误行为。
3. 禁止使用无法检索的随意字段名替代固定标签。
4. 禁止把已废弃逻辑留在注释中误导 AI。
5. 禁止写显而易见的注释，例如 `increment i`、`set name`。
6. 禁止保留过期注释、废弃逻辑说明。

## 必须注释的对象

- 公开类、公开接口、公开类型。
- 跨模块入口。
- 生命周期函数。
- 公共函数、异步函数、事件回调。
- 数据读写、配置读取、资源加载。
- 任何存在副作用、缓存、并发、状态切换或错误降级的函数。

## 固定检索标签

为方便 AI 使用 `rg`、`grep` 快速定位，注释使用以下英文标签。标签大小写保持一致。

- `Layer:` 所属分层，例如 core、module、manager、ui、data、platform。
- `Responsibility:` 当前对象负责什么。
- `Non-responsibility:` 当前对象明确不负责什么。
- `Contract:` 调用方和实现方必须遵守的稳定契约。
- `Preconditions:` 调用前必须满足的条件。
- `Postconditions:` 调用完成后必须成立的结果。
- `Parameters:` 参数含义、单位、范围、空值规则。
- `Returns:` 返回值含义和空值规则。
- `Side effects:` 状态修改、事件、日志、存储、网络、UI 切换等副作用。
- `Error behavior:` 异常、失败返回、fallback、日志、重试和降级行为。
- `Concurrency:` 线程、异步、重入、并发和取消规则。
- `Data source:` 数据来源，例如 JSON、缓存、远端、运行态状态。
- `Extension:` 推荐扩展方式。
- `AI note:` 专门给 AI 的维护提示，例如“不要在这里加类型分支”。

不是每段注释都必须包含所有标签，但公开边界至少包含 `Responsibility:`、`Contract:`、`Side effects:`、`Error behavior:` 中与当前对象相关的内容。

## 类注释规则

类注释必须说明：

- 类的职责范围。
- 所属分层或模块。
- 主要协作对象。
- 生命周期或所有权。
- 关键状态和副作用。
- 推荐扩展方式。

## 接口注释规则

接口注释必须说明：

- 接口抽象的能力边界。
- 实现方必须保证的行为。
- 调用方可以依赖的稳定契约。
- 允许的错误、空结果或降级行为。
- 是否允许异步、重入、缓存和并发调用。

## 函数注释规则

函数注释必须说明：

- 函数做什么，以及完成后的可观察结果。
- 参数含义、单位、范围、是否可为空。
- 返回值含义；无返回值时说明副作用。
- 前置条件和后置条件。
- 副作用，例如修改状态、触发事件、写入存储、切换 UI、发起网络请求。
- 错误行为，例如抛异常、返回失败结果、记录日志、使用 fallback。
- 异步函数必须说明完成时机、取消行为和并发限制。

## 统一示例

实际项目可以按语言语法替换注释符号，但保留字段和信息结构。

### 类注释示例

```text
/**
 * Coordinates active gameplay modules for a single match.
 *
 * Layer: manager.
 * Responsibility: creates, starts, pauses, resumes, and disposes gameplay modules.
 * Non-responsibility: does not implement gameplay rules, UI rendering, platform APIs, or data persistence.
 * Contract: registered modules must expose stable lifecycle methods and unique module ids.
 * Side effects: may change module lifecycle state and emit lifecycle logs.
 * Error behavior: rejects duplicate module ids and reports lifecycle failures to the scheduler.
 * Extension: add a new gameplay module implementation instead of adding type branches here.
 * AI note: keep this class focused on lifecycle coordination.
 */
class GameplayModuleManager {
}
```

### 接口注释示例

```text
/**
 * Defines the stable lifecycle contract for a gameplay module.
 *
 * Layer: module.
 * Responsibility: exposes module identity and lifecycle operations to the scheduler.
 * Non-responsibility: does not define gameplay-specific rules or UI behavior.
 * Contract: implementations must be deterministic for the same input state.
 * Error behavior: implementations must report startup failure without partially entering the running state.
 * Concurrency: lifecycle calls are not reentrant unless the implementation explicitly documents otherwise.
 * AI note: keep module-specific rules inside implementations; do not widen this interface for one module only.
 */
interface GameplayModule {
  moduleId: string
}
```

### 函数注释示例

```text
/**
 * Registers a gameplay module and makes it available for lifecycle scheduling.
 *
 * Responsibility: stores one module instance under its unique module id.
 * Parameters:
 * - module: module instance to register. Must not be null. moduleId must be unique.
 * Returns: true when the module is registered; false when the id already exists.
 * Preconditions: the manager must not be disposed.
 * Postconditions: successful registration makes the module visible to scheduler queries.
 * Side effects: stores the module reference and writes a registration log entry.
 * Error behavior: throws or reports argument error when module is null.
 * AI note: do not start the module here; startup is controlled by the scheduler.
 */
function registerModule(module) {
}
```

### 异步函数注释示例

```text
/**
 * Loads the level configuration used to initialize the current match.
 *
 * Responsibility: reads, parses, and validates level configuration data.
 * Parameters:
 * - levelId: stable level identifier. Must match an entry in the level data table.
 * - cancelToken: optional cancellation signal. Cancellation must prevent state mutation.
 * Returns: parsed level configuration. Never returns null after success.
 * Preconditions: level data files must be available in the configured data directory.
 * Postconditions: returned configuration has passed schema and range validation.
 * Side effects: reads JSON data from disk or asset storage; does not mutate gameplay state.
 * Error behavior: reports a missing-config error when levelId is not found.
 * Concurrency: safe to call concurrently for different level ids.
 * Data source: level JSON files under the runtime data directory.
 * AI note: keep numeric defaults in data files, not in this loader.
 */
async function loadLevelConfig(levelId, cancelToken) {
}
```