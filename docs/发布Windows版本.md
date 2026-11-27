# 发布 Windows 版本

OnlyShell 提供 Windows x64 的 Self-contained（内置 .NET 10 Desktop Runtime）和 Framework-dependent（缺少运行时时联网引导安装）两种变体。两者使用 Inno Setup 目录选择向导调用 Velopack 部署，以当前用户权限安装；应用尚未进行代码签名。

## 版本、命名和兼容性约定

- `Directory.Build.props` 的 `Version` 是源码版本。`onlytools.config.json` 的 `build.versionFiles` 指向该文件，使用 `scripts/check_product_version.py` 校验，不使用面向 Tauri 的旧版 `ods.py validate-version`。
- 负责人批准的规范源码 Tag 为 `vMAJOR.MINOR.PATCH`；当前稳定更新通道暂不支持预发布版本。
- 每个版本保留 `v<版本>-self-contained`、`v<版本>-framework-dependent` 两个变体 Release，以及 `v<版本>` 版本索引 Release。索引不承载更新文件，只链接两个变体。三者标题均为 `OnlyShell v<版本>`，变体由 Tag 和说明区分。
- Inno 安装向导名为 `OnlyShell-SelfContained-v<版本>-win-x64-Setup.exe` 或 `OnlyShell-FrameworkDependent-v<版本>-win-x64-Setup.exe`。
- Velopack 包 ID 仍为 `OnlyShellSelfContained` / `OnlyShellFrameworkDependent`，通道仍为 `win-x64-self-contained` / `win-x64-framework-dependent`。工具生成的 nupkg、引导安装器、便携 ZIP 和 JSON 索引名称作为规范的产品兼容性例外保留，不擅自重命名。
- 历史 Tag、Release、附件和安装路径不重写。数据继续保存在 `%LOCALAPPDATA%\OnlyShell`，凭据保存在当前用户的 Windows 凭据管理器；卸载保留数据。

## 本地验证与候选构建

先更新 README、CHANGELOG、对应版本的 Release Notes 和源码版本，再运行：

```powershell
python scripts/ods.py validate-config --config onlytools.config.json
python scripts/ods.py validate-readme --readme README.md
python scripts/check_product_version.py --version 1.0.7
python scripts/ods.py validate-changelog --version 1.0.7
python scripts/ods.py validate-release --notes RELEASE-NOTES-v1.0.7.md --version 1.0.7
python -m unittest discover -s scripts -p 'test_*.py'
dotnet build OnlyShell.sln -c Release
dotnet test TerminalPoc/VirtualTerminal-upstream/VirtualTerminal.Tests/VirtualTerminal.Tests.csproj -c Release
```

安装 Velopack CLI 1.2.0 与 Inno Setup 6 后，构建两种实际候选安装包：

```powershell
dotnet tool install --global vpk --version 1.2.0
./scripts/build-release.ps1 -Version 1.0.7
```

脚本不会安装或发布软件，输出在 `artifacts/release/<版本>/assets/<变体>/`。发布输入必须先提交，确保清单中的提交号对应实际源码。默认拒绝覆盖已有输出；重试时指定新的 `-OutputRoot`。可用 `-VpkPath`、`-InnoPath` 指定已安装工具。只有可信 Tag 工作流传入 `-PreviousRepository onlytools-lab/onlyshell`，从前一公开包生成差分。

每个变体包含实际文件的 `SHA256SUMS.txt` 与 `RELEASE-MANIFEST.json`，记录源码提交、版本、通道、大小和 SHA-256。校验器验证精确文件清单、包内身份/版本、便携入口和更新索引内的包大小/哈希；它不证明软件行为或签名可信。

## GitHub CI 与草稿

1. 推送候选分支并建立 PR。`ODS validation` 校验元数据、文档、版本和发布资产校验器测试；Windows job 构建、运行上游终端测试，并打包两种变体上传为 CI artifact，不创建 Release。
2. 审阅 PR 后，由负责人明确批准合并及 Tag。推送规范源码 Tag 后，`Release Windows Drafts` 再次执行门禁、构建、测试和差分打包。
3. 工作流创建两个变体草稿，下载 GitHub 上实际存储的附件并重新验证清单，随后创建规范版本索引草稿。没有自动公开发布步骤，也不覆盖已有草稿或资产。
4. 若工作流失败，可能已留下部分草稿。先检查故障和现存附件；不要删除或覆盖后盲目重跑，更不能自动转正式。
5. 验收通过后取得负责人对具体提交、Tag、三个 Release 及公开发布的明确授权。公开两个变体后，再公开版本索引；不要通过发布索引修改哪个变体属于“最新”的选择。

校验下载的变体草稿示例（完整源码 SHA 来自已批准提交）：

```powershell
python scripts/release_assets.py --directory <下载目录> --version 1.0.7 --variant self-contained --source-sha <完整提交号>
```

## 发布验收及限制

- 核对源码 Tag、应用版本、清单、包 ID、通道、Release 标题、真实文件清单、SHA-256 和说明中的下载地址。
- 下载真实 GitHub 资产，在隔离 Windows 环境验证两种安装包的启动、自定义路径、1.0.6 到候选版本的升级、重启、卸载及用户数据/凭据保留；不要覆盖日常使用的安装实例。
- 草稿不会被匿名客户端发现。草稿验收可以验证实际附件与受控更新源，但不能宣称公开自动更新已通过。公开后还需核验匿名下载、现有客户端的更新发现、用户点击下载/重启的完整路径以及两种通道各自的目标。
- 应用现有更新 URL 为 `corizhang/OnlyShell`，仓库已迁移至 `onlytools-lab/onlyshell`。本次保留客户端 URL，通过实际测试核对 GitHub 重定向和公开资产访问；不要把写权限令牌嵌入客户端。
- 每 24 小时最多检查一次更新，验收应记录该节流机制，不能把未触发检查当作检查成功。
- 干净 Windows 10/11、缺少 .NET Desktop Runtime 的联网引导安装和签名验证仍需对应环境与证据；已有运行时的单台电脑测试不能替代。

## 规范维护方反馈

当前基线 ODS 的 `validate-version` 默认依赖 Tauri；WPF 产品应配置独立的 MSBuild 版本检查器。Velopack 双变体的历史 Tag 与生成资产名需要产品适配，不能直接套用单安装包模板。已在产品配置和本文记录例外；自动化校验通过不代表行为验收或负责人发布批准。
