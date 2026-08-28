# DataCore CLI

DataCore CLI 将 DataCore 平台能力提供给终端、自动化程序和 AI Agent。首版覆盖完整的电导率预测迭代流程，并随安装包提供可安装的 DataCore Skills。

CLI 始终以当前登录的 DataCore 用户执行，沿用平台项目、实验和操作权限。写操作与云端计算必须显式确认。

完整文档与 Agent 可读入口：[datacore-cli.dp.cd.mba](https://datacore-cli.dp.cd.mba)

## 一键安装

需要 Python 3.10 或更高版本。安装仅写入当前用户目录，不需要管理员或 `sudo` 权限。

### macOS / Linux

```bash
curl -fsSL https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.sh | sh
```

### Windows PowerShell

```powershell
irm https://github.com/dptech-yb/datacore-cli/releases/latest/download/install.ps1 | iex
```

需要固定版本或不执行引导时，也可以直接安装 GitHub Release 中的 wheel：

```bash
python -m pip install https://github.com/dptech-yb/datacore-cli/releases/download/v0.1.0/datacore_cli-0.1.0-py3-none-any.whl
datacore setup
```

安装脚本会验证 Release 中 wheel 的 SHA256，然后安装 CLI、同步 Skills 并引导浏览器授权。密码、飞书和 Bohrium 登录最终均授权给当前 DataCore 平台账号。

## 快速开始

```bash
datacore setup
datacore doctor
datacore auth status
datacore skills list
```

电导轮次可以使用完整 DataCore 页面链接或 `round` 编号：

```bash
datacore --json conductivity status 'https://datacore.dp.qifalab.cn/experiments/123?tab=big-device&flow=conductivity&boChain=18&boTurn=2'
datacore conductivity export round28002 --format unilab --output task.xls
datacore conductivity validate round28002 measured.csv
datacore conductivity upload round28002 measured.csv --yes
datacore conductivity train round28002 --wait --yes
datacore conductivity retry-fold round28002 --fold 3 --yes
```

完整约定见内置 Skills：

- `datacore`：平台访问、安全与命令约定。
- `datacore-conductivity`：电导率预测迭代工作流。

## 自动化与 CI

无桌面环境使用短期、可撤销的 `DATACORE_TOKEN`，不要把 Token 写入仓库或命令历史：

```bash
export DATACORE_TOKEN='...'
datacore --json conductivity status round28002
```

成功输出包含 `ok`、`command`、`summary`、`data`、`artifacts` 和 `warnings`；失败输出包含稳定的 `code`、`message`、`action`、`retryable` 和 `details`。

## 更新与卸载

```bash
datacore update
datacore uninstall --yes
```

也可以重新运行对应平台的安装脚本。重复安装是幂等的，并会同步最新 Skills。

## 发布可信度

每个 GitHub Release 同时提供：

- wheel 与源码包；
- `SHA256SUMS`；
- CycloneDX SBOM；
- Sigstore 签名 bundle；
- GitHub Artifact Attestation 构建来源证明。

安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。
