# CLI 命令参考

> 本页由 CLI 参数定义自动生成。命令变更后，文档构建会同步更新并检查差异。

## `datacore setup`

安装 Skills 并登录 DataCore

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--no-browser` | — |
| `--allow-file-credential` | — |

## `datacore doctor`

检查 CLI、Skills、网络和授权状态

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore update`

升级 CLI 并同步 Skills

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--version` | — |

## `datacore uninstall`

撤销授权并卸载 CLI 与 Skills

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--yes` | — |

## `datacore auth login`

在浏览器中授权当前设备

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--no-browser` | — |
| `--allow-file-credential` | — |

## `datacore auth logout`

撤销当前设备授权

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore auth status`

查看当前登录身份与授权状态

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore skills install`

将内置 Skills 同步到本机

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--force` | — |

## `datacore skills list`

列出 CLI 自带的 Skills

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore conductivity status`

查看轮次状态与下一步动作

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore conductivity recommend`

提交本轮推荐配方计算

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--yes` | — |
| `--wait` | — |
| `--timeout` | — |

## `datacore conductivity export`

导出 UniLab、称量单或示例文件

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--format` | — |
| `--output` | — |
| `--total-mass-g` | — |

## `datacore conductivity train`

提交五折训练并跟踪状态

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--yes` | — |
| `--wait` | — |
| `--timeout` | — |

## `datacore conductivity compare`

比较当前模型与推荐基线

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore conductivity next`

确认并开启下一轮

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--yes` | — |

## `datacore conductivity validate`

只读校验实测 CSV

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |
| `file` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |

## `datacore conductivity upload`

校验并上传实测 CSV

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |
| `file` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--yes` | — |
| `--no-merge` | — |

## `datacore conductivity retry-fold`

只重试一个未完成训练折

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--fold` | — |
| `--yes` | — |

## `datacore conductivity decide`

记录继续或停止的轮次结论

### 参数

| 名称 | 必填 | 可选值 |
| --- | --- | --- |
| `target` | 是 | — |
| `decision` | 是 | continue / stop |

### 选项

| 选项 | 说明 |
| --- | --- |
| `--base-url` | — |
| `--json` | — |
| `--request-id` | 为本次调用指定可追踪请求 ID |
| `--timeout` | HTTP 请求超时秒数 |
| `--version` | show program's version number and exit |
| `--reason` | — |
| `--yes` | — |
