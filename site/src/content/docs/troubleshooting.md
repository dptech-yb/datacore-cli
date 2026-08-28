---
title: 故障恢复
description: 处理身份、权限、数据校验、Bohrium、长任务和五折部分失败。
---

先运行：

```bash
datacore doctor
datacore auth status
datacore --json conductivity status TARGET
```

## 登录或授权失效

重新运行 `datacore auth login`。不要借用或索取其他人的 Token。

## 权限不足

当前 DataCore 用户没有目标项目或实验权限。确认项目成员关系；不要切换身份或绕过后端判断。

## 实测文件校验失败

先执行只读的 `validate`。根据返回的行、列、推荐编号或数值问题修正文件，再上传。上传时服务端还会复检。

## Bohrium 凭据错误

由用户在 DataCore 中管理自己的 AccessKey 与项目号。CLI 不使用平台默认凭据，也不会要求在聊天或命令行中输入密钥。

## 本地等待超时

云端任务可能仍在执行。先查询 `status`，不要直接重复提交。

## 五折只有部分失败

状态会分别显示五折。使用 `retry-fold --fold N --yes` 只补交失败或未启动的折，已完成的折不会重建。

## 临时服务错误或限流

查看错误中的 `retryable` 和 `action`。可重试错误使用有限次数的退避重试，重试前仍需先查状态，避免重复创建任务。
