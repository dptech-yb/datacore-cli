---
title: 结构化输出约定
description: 给自动化程序和 Agent 使用的 JSON 成功、失败与文件产物约定。
---

自动化程序和 Agent 应始终加全局选项 `--json`。

## 成功

```json
{
  "ok": true,
  "command": "conductivity.status",
  "summary": "当前轮次状态已获取",
  "data": {},
  "artifacts": [],
  "warnings": []
}
```

- `summary`：可直接展示给用户的简短结论；
- `data`：命令相关结构化结果；
- `artifacts`：生成文件的路径、大小和类型；
- `warnings`：不阻断操作但需要用户知道的信息。

## 失败

```json
{
  "ok": false,
  "error": {
    "code": "permission_denied",
    "message": "当前用户无权访问目标实验",
    "action": "请确认项目成员关系或联系项目管理员。",
    "retryable": false,
    "details": {}
  }
}
```

Agent 应优先遵循 `action`，并根据 `retryable` 判断是否能做有限重试。权限、校验和生命周期错误不是可绕过的客户端限制。

## 请求追踪

```bash
datacore --request-id my-run-20260828 --json conductivity status TARGET
```

为自动化调用设置稳定请求 ID，便于把客户端日志与 DataCore 服务端审计关联起来。
