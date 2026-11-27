# OnlyShell v1.0.7

## Highlights

- 修正主机/终端菜单交互，以及没有 SSH 会话时错误显示服务器监控的问题。
- 修正 Windows SFTP 下载文件锁、RSA SHA-2 认证优先级和远端符号链接检查问题。
- 增加版本与文档检查、最终资产 SHA-256 清单和先生成草稿的发布流程。

## Compatibility

- Windows x64；本轮本地验证环境为 Windows 10 19045、.NET 10.0.13。
- Self-contained 内置 .NET 10 Desktop Runtime；Framework-dependent 需要该运行时，安装器可联网引导安装。
- 沿用 `OnlyShellSelfContained` / `OnlyShellFrameworkDependent` 包 ID、各自更新通道及 `%LOCALAPPDATA%\OnlyShell` 数据目录；本次没有数据库格式迁移。
- 安装向导以当前用户运行。安装包和应用尚未进行代码签名。

## Known Issues

- 干净 Windows 11 和缺少 .NET 时的联网引导安装尚未完成验收。
- GitHub 实际发布资产下载、1.0.6 到本版本的线上更新和用户点击更新提示的完整流程，需要在候选资产生成后继续验收；本说明不将这些项目描述为已通过。
- 终端剪贴板、拖放传输队列界面以及 SSH 凭据保存/遗忘界面的完整人工验收尚未覆盖。
- 符号链接保护增加父目录列表读取，大目录性能尚未基准测试。

## Downloads

根据当前安装的版本选择同一变体，避免切换更新通道：

- `OnlyShell-SelfContained-v1.0.7-win-x64-Setup.exe`：自包含安装向导。
- `OnlyShell-FrameworkDependent-v1.0.7-win-x64-Setup.exe`：依赖 .NET 的安装向导。
- 每个变体同时提供 `SHA256SUMS.txt` 和 `RELEASE-MANIFEST.json`，由最终文件实际生成；附带的 Velopack 包、便携 ZIP、引导安装器和更新索引保留工具生成的名称，属于兼容性例外。
- 自包含版：[下载页面](https://github.com/onlytools-lab/onlyshell/releases/tag/v1.0.7-self-contained)。
- 依赖运行时版：[下载页面](https://github.com/onlytools-lab/onlyshell/releases/tag/v1.0.7-framework-dependent)。

## Verification

- 修复后的应用 Release 本地构建通过，0 个警告、0 个错误；该结果针对本轮功能修复，候选版本将由 CI 再次构建。
- 本地 Ubuntu 24.04 / OpenSSH 9.6 容器验证 15/15 项通过，包括认证、交互式 shell、脚本、监控和 SFTP；并非公网独立主机验收。
- 隔离应用完成 GitHub Device Flow、私有测试仓库的拉取/解密/导入/推送及重启持久化；远端仅含虚构测试主机。
- 独立 QA 包验证了两种变体的自定义路径安装、本地更新源升级、数据保留和卸载；不是正式 1.0.7 产物的线上更新证明。
- 草稿生成后需下载实际 GitHub 资产验证哈希、版本、来源提交和更新通道；通过后再批准公开发布。
- 发布资产校验器 10 项本地测试通过；终端测试在修正两条不符合默认 CR/LF 模式的旧断言并覆盖两种 LNM 模式后，156 项通过。未修改终端解码器或键盘编码器实现。
