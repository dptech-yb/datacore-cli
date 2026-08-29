---
title: 身份、授权与权限
description: 了解 DataCore CLI 如何登录、保存凭据，以及沿用平台权限。
---

CLI 没有独立账号体系。它只代表当前用户调用 DataCore，因此网页、终端与 Agent 看到的是同一套数据范围和操作权限。

## 1. 登录 DataCore 平台账号

```bash
datacore auth login
```

命令会打开 [DataCore 授权页](https://datacore.dp.qifalab.cn/)。用户可以使用平台密码、飞书或 Bohrium 登录；无论入口是什么，最终都解析为同一个 DataCore 用户身份。

CLI 不创建第二套账号，也不拥有独立的数据权限。项目、实验、数据和操作权限全部由 DataCore 后端统一判断。

## 2. 凭据如何保存

- 交互式登录默认把可撤销的短期授权保存到操作系统 Keychain；
- 无桌面环境使用 `DATACORE_TOKEN`，不要写进仓库或命令历史；
- 本地文件保存默认关闭，只有用户明确传入 `--allow-file-credential` 才启用；
- Bohrium AccessKey 不出现在命令参数、日志、Prompt 或导出文件中。

## 3. 查看与撤销

```bash
datacore auth status
datacore auth logout
```

用户也可以在 DataCore 个人中心查看和撤销已经授权的 CLI 客户端。撤销后，本机持有的旧授权不能继续访问平台。

## 4. 权限如何生效

| 场景 | 判断位置 | CLI 行为 |
| --- | --- | --- |
| 查看项目或实验 | DataCore 后端 | 仅返回当前用户有权看到的数据 |
| 上传、训练、开启下一轮 | DataCore 后端 + 用户确认 | 目标冻结后仍需 `--yes` |
| Bohrium 计算 | 当前用户的平台配置 | 不借用平台默认项目或他人凭据 |
| 撤销设备 | DataCore 个人中心或 CLI | 旧授权立即失效 |

## 5. 自动化额度

```bash
datacore --json quota
```

CLI、Skills 和第三方 Agent 按 DataCore 用户共用查询、写操作、工具执行与云端计算额度。额度每天北京时间 00:00 自动进入新周期，不依赖定时清库；换设备或重新授权不会绕过限制。管理员可以在 DataCore「管理 → 自动化额度」中设置长期覆盖、增加今日额度或恢复默认值。

## 6. 写操作确认

查询和校验可以直接执行；上传、推荐、训练、重试、决策和开启下一轮等操作必须先确认目标，再传入 `--yes`。这一约束同时适用于人和 Agent。
