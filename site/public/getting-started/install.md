# 安装与快速开始

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
3. 安装 CLI，并准备同步 DataCore Skills。

## 2. 初始化并检查

```bash
datacore setup
datacore doctor
datacore auth status
datacore skills list
```

`datacore setup` 会同步 Skills，并在浏览器中打开 [DataCore 平台](https://datacore.dp.qifalab.cn/)授权页。密码、飞书和 Bohrium 登录最终都绑定到当前平台账号。

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
  | sh -s -- --version v0.2.1 --no-setup
```

也可以从 [GitHub Releases](https://github.com/dptech-yb/datacore-cli/releases) 下载 wheel、校验和、SBOM 和 Sigstore bundle。

## 更新、重装与卸载

```bash
datacore update
datacore uninstall --yes
```

更新会同步 CLI 与 Skills。卸载会撤销当前设备授权，并清理 CLI 与 DataCore Skills。

遇到安装或授权问题，请先查看[故障恢复](/troubleshooting/)；完整参数见[CLI 命令参考](/reference/commands/)。
