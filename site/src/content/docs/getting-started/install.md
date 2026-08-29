---
title: 安装与快速开始
description: 在 macOS、Linux 或 Windows 安装 DataCore CLI，并完成平台授权。
---

DataCore CLI 需要 Python 3.10 或更高版本。安装程序只写入当前用户目录，不需要管理员权限。

> 完成本页后，你应当可以运行 `datacore doctor`、看到已安装的 Skills，并以自己的 DataCore 账号完成授权。

## 1. 安装 CLI 与 Skills

### macOS / Linux

```bash
curl -fsSL https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.sh | sh
```

### Windows PowerShell

```powershell
irm https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.ps1 | iex
```

一键安装会完成：

1. 从官方 GitHub Release 下载 wheel；
2. 用同一 Release 的 `SHA256SUMS` 校验文件；
3. 安装 CLI，并把 Skills 同步到开放 Agent Skills 目录；
4. 自动适配本机已有的 Claude Code、Codex、Continue、Trae 等 Agent。

Skills 的统一来源是 `~/.agents/skills`。需要专属目录的 Agent 会使用指向统一来源的链接；Windows 或不支持符号链接的文件系统会自动回退为复制。升级自 v0.1—v0.3 时，原有 `~/.codex/skills` 内容会迁移；若检测到用户修改，安装程序会先备份再替换。

## 2. 初始化并检查

```bash
datacore setup
datacore doctor
datacore auth status
datacore skills list
datacore skills read datacore
```

`datacore setup` 会同步 Skills，并在浏览器中打开 [DataCore 平台](https://datacore.dp.qifalab.cn/)授权页。密码、飞书和 Bohrium 登录最终都绑定到当前平台账号。

### 使用标准 Skills 管理器

CLI 已安装、但需要给另一种 Agent 单独同步 Skills 时，可以使用开放 Skills 管理器：

```bash
npx skills add https://datacore-cli.dp.cd.mba -g -y
```

它会从 DataCore 的标准发现地址读取 Skills，并适配其支持的 Agent。没有 Node.js 时不影响一键安装；DataCore 自带安装器仍会完成通用目录和已检测 Agent 的同步。

未被自动识别的非通用 Agent，也可以明确指定：

```bash
datacore skills install --agent claude-code --force
datacore skills install --agent '*' --force
```

### 让 Agent 独立完成安装

如果运行环境无法打开浏览器，在 DataCore [`/cli`](https://datacore.dp.qifalab.cn/cli) 生成一次性 Agent 安装指令并复制给 Agent。它会安装 CLI 与 Skills，然后通过标准输入执行 `datacore setup --install-token-stdin --allow-file-credential`。安装 Token 约 10 分钟有效、只可兑换一次，正式凭据不会出现在命令参数或回复中。

看到以下结果即可开始使用：

- `doctor` 未报告阻断性问题；
- `auth status` 显示当前用户；
- `skills list` 至少包含 DataCore 基础 Skill 与电导 Skill。

## 3. 执行第一条工作流命令

从 DataCore 电导页面复制完整 URL，然后执行：

```bash
datacore --json conductivity status '完整的 DataCore 电导页面 URL'
```

命令只查询状态，不会修改实验。返回结果中的 `nextAction` 是当前轮次应执行的下一步。

## 固定版本

生产环境可以固定到明确版本：

```bash
curl -fsSL https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.sh \
  | sh -s -- --version v0.4.1 --no-setup
```

也可以从 [GitHub Releases](https://github.com/dptech-yb/datacore-cli/releases) 下载 wheel、校验和、SBOM 和 Sigstore bundle。

## 更新、重装与卸载

```bash
datacore update
datacore uninstall --yes
```

更新从官方 GitHub Release 下载 wheel，按同一 Release 的 `SHA256SUMS` 校验后安装，再同步 Skills；不依赖 PyPI。卸载会撤销当前设备授权，并清理 CLI 与 DataCore Skills。

遇到安装或授权问题，请先查看[故障恢复](/troubleshooting/)；完整参数见[CLI 命令参考](/reference/commands/)。
