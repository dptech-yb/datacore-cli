---
title: 安装与快速开始
description: 在 macOS、Linux 或 Windows 安装 DataCore CLI，并完成平台授权。
---

DataCore CLI 需要 Python 3.10 或更高版本。安装程序只写入当前用户目录，不需要管理员权限。

## macOS / Linux

```bash
curl -fsSL https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.sh | sh
```

## Windows PowerShell

```powershell
irm https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.ps1 | iex
```

安装脚本会完成三件事：

1. 从官方 GitHub Release 下载 wheel；
2. 用同一 Release 的 `SHA256SUMS` 校验文件；
3. 安装 CLI、同步 Skills，并打开 DataCore 授权页。

安装完成后检查：

```bash
datacore setup
datacore doctor
datacore auth status
```

`datacore setup` 会同步 DataCore Skills，并在浏览器中打开平台授权页。密码、飞书和 Bohrium 登录最终都绑定到当前 DataCore 平台账号。

## 固定版本

生产环境可以固定到明确版本：

```bash
curl -fsSL https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.sh \
  | sh -s -- --version v0.1.0 --no-setup
```

也可以从 [GitHub Releases](https://github.com/dptech-yb/datacore-cli/releases) 下载 wheel、校验和、SBOM 和 Sigstore bundle。

## 更新与卸载

```bash
datacore update
datacore uninstall --yes
```

更新会同步 CLI 与 Skills。卸载会撤销当前设备授权，并清理 CLI 与 DataCore Skills。
