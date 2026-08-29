---
title: 让第三方 Agent 使用 DataCore
description: 通过 CLI、结构化 JSON 和 Skills，让具备终端能力的 Agent 安全调用 DataCore。
---

DataCore Agent 不是唯一入口。任何能够执行本地命令、读取文本并获得用户确认的 Agent，都可以通过 DataCore CLI 使用同一套平台能力。

## 最短接入路径

1. 用户安装 CLI 并完成 `datacore setup`；
2. Agent 读取 DataCore 路由 Skill；只有电导任务才继续读取电导 Skill；
3. Agent 先执行只读状态查询；
4. 对写操作展示目标、影响和下一步，获得确认后再加 `--yes`；
5. 长任务提交后查询状态，不因本地等待中断而重复创建任务。

```bash
datacore --json project list
datacore --json quota
```

Agent 只需要处理三个稳定界面：

| 界面 | 用途 | 首选入口 |
| --- | --- | --- |
| Skills | 理解工作流、确认与恢复规则 | `datacore skills list` |
| CLI | 执行确定性操作 | `datacore …` |
| JSON | 读取结果、错误和产物 | 全局 `--json` |

## Skills 在哪里

安装包会把 Skills 同步到本机支持的 Agent 目录。其他 Agent 也可以直接读取公开版本：

- [DataCore 基础 Skill](/skills/datacore/SKILL.md)
- [电导工作流 Skill](/skills/datacore-conductivity/SKILL.md)

如果 Agent 不支持 Skill 发现机制，也可以读取 [llms.txt](/llms.txt)、[完整上下文](/llms-full.txt) 和 [commands.json](/commands.json)。

## 最小执行循环

```text
读取 Skill → 查询状态 → 向用户说明目标与影响
           → 获得确认 → 执行写操作 → 查询服务端状态
```

本地等待结束不代表云端任务失败。Agent 必须先重新查询状态，再决定是否重试。

## 为什么统一走 CLI

- **权限一致**：Agent 与网页使用同一 DataCore 用户；
- **业务规则一致**：不在 Prompt、脚本或不同 Agent 中重复实现校验逻辑；
- **错误一致**：稳定错误码会给出明确的恢复动作；
- **额度一致**：CLI、Skills 和不同 Agent 共用同一用户额度与北京时间重置周期；
- **可替换**：Agent 可以增加、替换或下线，不影响平台核心工作流。

## 不要这样做

- 不要让用户在聊天中发送 Bohrium AccessKey；
- 不要绕过 DataCore 返回的权限、校验或生命周期错误；
- 不要把本地等待超时当成云任务失败；
- 不要在未确认时上传、训练或开启下一轮。
