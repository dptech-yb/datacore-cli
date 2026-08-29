# DataCore CLI

DataCore CLI 将 DataCore 平台的普通用户能力提供给终端、自动化程序和 AI Agent。当前版本覆盖项目、实验、物质、工站预约、试剂任务、数据工具记录与完整电导率预测迭代，并随安装包提供可安装的 DataCore Skills。

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
python -m pip install https://github.com/dptech-yb/datacore-cli/releases/download/v0.3.0/datacore_cli-0.3.0-py3-none-any.whl
datacore setup
```

安装脚本会验证 Release 中 wheel 的 SHA256，然后安装 CLI、同步 Skills 并引导浏览器授权。密码、飞书和 Bohrium 登录最终均授权给当前 DataCore 平台账号。

### 交给 Agent 安装

无法打开浏览器或回传授权链接时，在 DataCore 的 `/cli` 页面生成“Agent 安装指令”，复制整段给 Agent。指令中的 `dc_install_…` Token 约 10 分钟有效、只能兑换一次；Agent 通过标准输入执行：

```bash
datacore setup --install-token-stdin --allow-file-credential
```

兑换后的正式凭据直接写入系统钥匙串；无钥匙串环境只有在上述明确选项下才保存为权限 `0600` 的本地文件。CLI 不打印正式凭据，授权可在个人中心随时撤销。

## 快速开始

```bash
datacore setup
datacore doctor
datacore auth status
datacore skills list
datacore --json capabilities
datacore --json quota
```

日常平台查询：

```bash
datacore --json project list
datacore --json experiment list
datacore --json chemical search 'LiPF6'
datacore --json booking list --year 2026 --month 8
datacore --json reagent inventory --q EC
datacore --json tool history --limit 20
```

创建或修改使用明确的 JSON 文件并显式确认；例如：

```bash
datacore project create --file project.json --yes
datacore booking create --file booking.json --yes
```

专业电导轮次可以使用完整 DataCore 页面链接或 `round` 编号：

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

额度按 DataCore 用户累计，CLI、Skills 和第三方 Agent 共用；每天北京时间 00:00 自动进入新周期。运行 `datacore quota` 查看剩余量，管理员可在平台管理页设置长期覆盖或仅今日加额。

## 自动化与 CI

受管 CI 可以通过机密变量提供可撤销的 `DATACORE_TOKEN`，不要把 Token 写入仓库或命令历史。普通无桌面 Agent 优先使用上面的一次性安装指令：

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
