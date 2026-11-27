# Changelog

记录面向用户的版本变化；历史版本详情见 GitHub Releases。

## [Unreleased]

## [1.0.7] - 2026-11-28

### Fixed
- 修正主机与终端菜单的显示、目标选择和对话框交互；分组不再误用主机右键菜单。
- 没有 SSH 会话时隐藏服务器监控，避免显示未绑定的监控面板。
- SFTP 下载在校验、打开或替换临时文件前释放写入流，避免 Windows 文件锁导致下载失败。
- RSA 私钥认证优先使用 SHA-2 签名，兼容禁用 SHA-1 的 OpenSSH 服务端。
- SFTP 操作先检查父目录中的实际条目，防止最终路径的符号链接被提前解析并跟随。

### Changed
- 接入发布前文档、版本与资产校验；安装包名称包含版本和架构，并提供 SHA-256 清单。
- 两种 Windows 安装包先生成 GitHub Release 草稿，验收和负责人授权后再公开；保留现有包 ID、更新通道和本机数据目录。

[Unreleased]: https://github.com/onlytools-lab/onlyshell/compare/v1.0.7...HEAD
[1.0.7]: https://github.com/onlytools-lab/onlyshell/releases/tag/v1.0.7
