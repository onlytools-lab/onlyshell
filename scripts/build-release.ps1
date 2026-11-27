param(
    [Parameter(Mandatory)][string]$Version,
    [string]$VpkPath = 'vpk',
    [string]$InnoPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    [string]$OutputRoot = 'artifacts/release',
    [string]$PreviousRepository = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = Split-Path -Parent $PSScriptRoot
function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE" }
}
Push-Location $repo
try {
    if ($Version -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') { throw 'Stable MAJOR.MINOR.PATCH required' }
    Invoke-Checked 'python' @('scripts/check_product_version.py', '--version', $Version)
    Invoke-Checked 'python' @('scripts/ods.py', 'validate-release', '--notes', "RELEASE-NOTES-v$Version.md", '--version', $Version)
    $source = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve source commit' }
    $dirty = & git status --porcelain --untracked-files=normal -- src TerminalPoc installer scripts Directory.Build.props onlytools.config.json .github README.md CHANGELOG.md 'RELEASE-NOTES-*' docs
    if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Commit release inputs before packaging so the manifest identifies the exact source' }
    $output = [IO.Path]::GetFullPath((Join-Path $OutputRoot $Version))
    if (Test-Path -LiteralPath $output) { throw "Output exists; choose a fresh OutputRoot: $output" }
    if (-not (Test-Path -LiteralPath $InnoPath -PathType Leaf)) { throw "Inno compiler not found: $InnoPath" }
    New-Item -ItemType Directory -Path $output -Force | Out-Null
    foreach ($variant in @('self-contained', 'framework-dependent')) {
        $selfContained = $variant -eq 'self-contained'
        $display = if ($selfContained) { 'SelfContained' } else { 'FrameworkDependent' }
        $packageId = "OnlyShell$display"
        $channel = "win-x64-$variant"
        $publish = Join-Path $output "$variant/publish"
        $packages = Join-Path $output "$variant/packages"
        $assets = Join-Path $output "assets/$variant"
        New-Item -ItemType Directory -Path $publish, $packages, $assets -Force | Out-Null
        Invoke-Checked 'dotnet' @('publish', 'src/OnlyShell.App/OnlyShell.App.csproj', '-c', 'Release', '-r', 'win-x64',
            '--self-contained', $selfContained.ToString().ToLowerInvariant(), '-o', $publish, "-p:Version=$Version")
        $productVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo((Join-Path $publish 'OnlyShell.dll')).ProductVersion.Split('+')[0]
        if ($productVersion -ne $Version) { throw "Published version mismatch: $productVersion" }
        # Prior public packages are used only by the trusted tag workflow for deltas.
        if ($PreviousRepository) {
            $previous = & gh release list --repo $PreviousRepository --exclude-drafts --exclude-pre-releases --limit 100 --json tagName | ConvertFrom-Json
            if ($LASTEXITCODE -ne 0) { throw 'Cannot enumerate previous releases' }
            if ($previous | Where-Object { $_.tagName -match "^v\d+\.\d+\.\d+-$variant$" }) {
                $downloadArgs = @('download', 'github', '--repoUrl', "https://github.com/$PreviousRepository", '--channel', $channel, '--outputDir', $packages)
                if ($env:GITHUB_TOKEN) { $downloadArgs += @('--token', $env:GITHUB_TOKEN) }
                Invoke-Checked $VpkPath $downloadArgs
            }
        }
        $packArgs = @('pack', '--packId', $packageId, '--packTitle', 'OnlyShell', '--packVersion', $Version,
            '--packDir', $publish, '--mainExe', 'OnlyShell.exe', '--channel', $channel, '--outputDir', $packages,
            '--icon', 'src/OnlyShell.App/Assets/OnlyShell.ico', '--releaseNotes', "RELEASE-NOTES-v$Version.md")
        if (-not $selfContained) { $packArgs += @('--framework', 'net10.0-x64-desktop') }
        Invoke-Checked $VpkPath $packArgs
        $bootstrapper = Join-Path $packages "$packageId-$channel-Setup.exe"
        Invoke-Checked $InnoPath @('/Qp', "/DAppVersion=$Version", "/DVariantName=$display", "/DVpkSetupPath=$bootstrapper", "/O$assets", 'installer/OnlyShell.iss')
        $installer = Join-Path $assets "OnlyShell-$display-v$Version-win-x64-Setup.exe"
        if ([Diagnostics.FileVersionInfo]::GetVersionInfo($installer).ProductVersion.Trim() -ne $Version) {
            throw 'Inno installer version mismatch'
        }
        foreach ($name in @("$packageId-$Version-$channel-full.nupkg", "$packageId-$channel-Setup.exe", "$packageId-$channel-Portable.zip")) {
            Copy-Item -LiteralPath (Join-Path $packages $name) -Destination $assets
        }
        $delta = Join-Path $packages "$packageId-$Version-$channel-delta.nupkg"
        if (Test-Path -LiteralPath $delta) { Copy-Item -LiteralPath $delta -Destination $assets }
        $feed = Get-Content -LiteralPath (Join-Path $packages "releases.$channel.json") -Raw | ConvertFrom-Json
        # All feed entries must be downloadable from this release, including deltas.
        $feed.Assets = @($feed.Assets | Where-Object { $_.Version -eq $Version })
        $feed | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $assets "releases.$channel.json") -Encoding utf8
        Invoke-Checked 'python' @('scripts/release_assets.py', '--directory', $assets, '--version', $Version,
            '--variant', $variant, '--source-sha', $source, '--write-manifest')
    }
    Write-Host "Both variants verified at $output/assets; nothing installed or published."
}
finally { Pop-Location }
