---
title: 全平台能力
description: 使用统一 CLI 查询和操作项目、实验、物质、预约、试剂与工具记录。
---

DataCore CLI 对外提供稳定的普通用户自动化入口，而不是开放全部内部 API。所有命令沿用当前 DataCore 身份、项目角色、实验资源资格和试剂组权限。

## 先看当前能力

```bash
datacore --json capabilities
datacore --json quota
```

能力目录用于判断当前版本是否已经开放某个操作；额度分为查询、写操作、工具执行和云端计算，每天北京时间 00:00 进入新周期。

## 项目与实验

```bash
datacore --json project list
datacore --json project show 7
datacore --json project lineage 7
datacore --json experiment list
datacore --json experiment show 68
datacore --json experiment lineage 68
```

写入使用 JSON 文件，便于人和 Agent 在提交前完整检查：

```bash
datacore project create --file project.json --yes
datacore project update 7 --file patch.json --yes
datacore experiment create 12 --file experiment.json --yes
datacore experiment update 68 --file patch.json --yes
```

删除、权限管理和系统配置仍保留在网页管理界面，不进入普通 CLI。

## 实验资源

```bash
datacore --json booking list --year 2026 --month 8
datacore --json booking qualified --station conductivity --material-state solid
datacore --json reagent inventory --q EC
datacore --json reagent tasks --status pending
datacore --json chemical search "LiPF6"
```

预约和试剂服务继续执行它们原有的权限与生命周期校验。CLI 不会自行判断操作员等级、预约冲突、实验组范围或库存可用性。

## 工具与专业工作流

```bash
datacore --json tool history --limit 50
datacore --json conductivity status '完整的 DataCore 电导页面 URL'
```

通用工具按能力逐项开放；电导预测迭代已有独立 Skill 和完整恢复约定。不要猜测或调用未列入 `capabilities` 的内部端点。

## 限流与加额

- 同一 CLI 命令编排的多个 HTTP 请求，在同一个日额度类别中只扣一次；
- 每分钟突发限制仍按原始请求计数，防止快速重试冲击平台；
- 额度属于 DataCore 用户，换 Token 或设备不能绕过；
- 管理员可以设置长期日额度、仅今日加额，或恢复平台默认值；所有调整都会进入审计记录。
