# 安全与发布可信度

## 权限边界

CLI 是 DataCore 的确定性执行层，不是权限代理。每个请求都以当前登录用户身份进入平台，后端继续执行项目、实验和操作权限判断。

## 凭据保护

- DataCore 授权优先保存在系统 Keychain；
- Bohrium AccessKey 由平台按用户加密管理，不进入 CLI 参数；
- 无桌面自动化使用可撤销的 `DATACORE_TOKEN`；
- 日志、Prompt、导出文件和错误详情不得包含秘密。

## 发布产物

每个 GitHub Release 提供：

- Python wheel 与源码包；
- SHA256 校验清单；
- CycloneDX SBOM；
- Sigstore 签名 bundle；
- GitHub Artifact Attestation 构建来源证明。

一键安装脚本会在安装前校验 wheel 的 SHA256。发布工作流从仓库标签自动构建，不使用开发者本机产物。

## 报告漏洞

请使用 GitHub 的私密漏洞报告，不要公开提交可能涉及凭据泄露、越权、命令注入或供应链篡改的问题。详见仓库 [SECURITY.md](https://github.com/dptech-yb/datacore-cli/blob/main/SECURITY.md)。
