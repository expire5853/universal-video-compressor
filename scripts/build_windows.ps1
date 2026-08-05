[CmdletBinding()]
param(
    [ValidateSet('Standalone', 'OneFile', 'Both')]
    [string]$Mode = 'OneFile',

    [bool]$BundleFfmpeg = $true,

    [string]$FfmpegPath,

    [string]$OutputRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $ProjectRoot 'src'
$EntryPoint = Join-Path $SourceRoot 'video_compressor'
$IconPath = Join-Path $ProjectRoot 'assets\video-compressor.ico'
$ReadmePath = Join-Path $ProjectRoot 'README.md'
$LicensePath = Join-Path $ProjectRoot 'LICENSE'
$VersionSourcePath = Join-Path $EntryPoint '__init__.py'
$UvCommand = Get-Command uv -ErrorAction Stop
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)

if (-not (Test-Path -LiteralPath $EntryPoint -PathType Container)) {
    throw "GUI package entry point not found: $EntryPoint"
}

if (-not (Test-Path -LiteralPath $VersionSourcePath -PathType Leaf)) {
    throw "Project version source not found: $VersionSourcePath"
}

$VersionSource = Get-Content -LiteralPath $VersionSourcePath -Raw -Encoding UTF8
$VersionMatch = [regex]::Match(
    $VersionSource,
    '(?m)^__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"\s*$'
)
if (-not $VersionMatch.Success) {
    throw "Unable to read the project version from $VersionSourcePath"
}
$ProductVersion = $VersionMatch.Groups['version'].Value
$FileVersion = "$ProductVersion.0"
$OneFileFlavor = 'system-ffmpeg'
if ($BundleFfmpeg) {
    $OneFileFlavor = 'bundled-ffmpeg'
}

if (-not (Test-Path -LiteralPath $IconPath -PathType Leaf)) {
    Write-Host 'Generating the Windows application icon...'
    $IconArguments = @(
        'run'
        '--project'
        $ProjectRoot
        '--frozen'
        '--group'
        'build'
        'python'
        (Join-Path $PSScriptRoot 'generate_icon.py')
    )
    & $UvCommand.Source @IconArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Icon generation failed with exit code $LASTEXITCODE"
    }
}

function Resolve-FfmpegTools {
    param([string]$RequestedPath)

    $Candidates = [System.Collections.Generic.List[string]]::new()
    if ($RequestedPath) {
        $Candidates.Add($RequestedPath)
    }

    $PathCommand = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($PathCommand) {
        $Candidates.Add($PathCommand.Source)
    }

    if ($env:LOCALAPPDATA) {
        $WinGetRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
        if (Test-Path -LiteralPath $WinGetRoot -PathType Container) {
            Get-ChildItem -LiteralPath $WinGetRoot -Directory -Filter 'Gyan.FFmpeg_*' |
                ForEach-Object {
                    Get-ChildItem -LiteralPath $_.FullName -Recurse -File -Filter 'ffmpeg.exe'
                } |
                Sort-Object LastWriteTime -Descending |
                ForEach-Object { $Candidates.Add($_.FullName) }
        }
    }

    foreach ($Candidate in $Candidates) {
        $Expanded = [Environment]::ExpandEnvironmentVariables($Candidate.Trim('"'))
        if (Test-Path -LiteralPath $Expanded -PathType Container) {
            $Expanded = Join-Path $Expanded 'ffmpeg.exe'
        }
        if (-not (Test-Path -LiteralPath $Expanded -PathType Leaf)) {
            continue
        }

        $ResolvedFfmpeg = (Resolve-Path -LiteralPath $Expanded).Path
        $ResolvedFfprobe = Join-Path (Split-Path -Parent $ResolvedFfmpeg) 'ffprobe.exe'
        if (Test-Path -LiteralPath $ResolvedFfprobe -PathType Leaf) {
            return [pscustomobject]@{
                Ffmpeg = $ResolvedFfmpeg
                Ffprobe = (Resolve-Path -LiteralPath $ResolvedFfprobe).Path
            }
        }
    }

    throw 'Unable to locate a matching ffmpeg.exe and ffprobe.exe pair.'
}

$FfmpegTools = $null
if ($BundleFfmpeg) {
    $FfmpegTools = Resolve-FfmpegTools -RequestedPath $FfmpegPath
    Write-Host "Bundling FFmpeg: $($FfmpegTools.Ffmpeg)"
    Write-Host "Bundling FFprobe: $($FfmpegTools.Ffprobe)"
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

function Invoke-NuitkaBuild {
    param(
        [ValidateSet('Standalone', 'OneFile')]
        [string]$BuildMode
    )

    $ModeDirectory = Join-Path $OutputRoot $BuildMode.ToLowerInvariant()
    New-Item -ItemType Directory -Force -Path $ModeDirectory | Out-Null

    $NuitkaArguments = @(
        '-m'
        'nuitka'
        '--enable-plugin=pyside6'
        '--python-flag=-m'
        '--assume-yes-for-downloads'
        '--mingw64'
        '--windows-console-mode=disable'
        "--windows-icon-from-ico=$IconPath"
        '--company-name=Universal Video Compressor Contributors'
        '--product-name=Video Compressor'
        '--file-description=Universal CPU GPU Video Compressor'
        "--file-version=$FileVersion"
        "--product-version=$ProductVersion"
        '--copyright=Copyright (c) 2026 Universal Video Compressor contributors'
        '--output-filename=VideoCompressor.exe'
        "--output-dir=$ModeDirectory"
        "--report=$(Join-Path $ModeDirectory 'compilation-report.xml')"
    )

    if ($BuildMode -eq 'OneFile') {
        $NuitkaArguments += '--onefile'
        $NuitkaArguments += (
            '--onefile-tempdir-spec={CACHE_DIR}/UniversalVideoCompressor/' +
            "$ProductVersion/$OneFileFlavor"
        )
    }
    else {
        $NuitkaArguments += '--standalone'
    }

    if ($BundleFfmpeg) {
        $NuitkaArguments += "--include-data-files=$($FfmpegTools.Ffmpeg)=tools/ffmpeg.exe"
        $NuitkaArguments += "--include-data-files=$($FfmpegTools.Ffprobe)=tools/ffprobe.exe"
    }

    $NuitkaArguments += $EntryPoint

    $UvArguments = @(
        'run'
        '--project'
        $ProjectRoot
        '--frozen'
        '--group'
        'build'
        '--python=3.12'
        'python'
    ) + $NuitkaArguments

    Write-Host "Building $BuildMode package in $ModeDirectory"
    & $UvCommand.Source @UvArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka $BuildMode build failed with exit code $LASTEXITCODE"
    }

    if ($BuildMode -eq 'OneFile') {
        $Executable = Join-Path $ModeDirectory 'VideoCompressor.exe'
    }
    else {
        $Executable = Join-Path $ModeDirectory 'video_compressor.dist\VideoCompressor.exe'
    }
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Nuitka finished but the expected executable is missing: $Executable"
    }

    if ($BundleFfmpeg) {
        $FfmpegRoot = Split-Path -Parent (Split-Path -Parent $FfmpegTools.Ffmpeg)
        $FfmpegLicense = Join-Path $FfmpegRoot 'LICENSE'
        if (Test-Path -LiteralPath $FfmpegLicense -PathType Leaf) {
            Copy-Item -LiteralPath $FfmpegLicense -Destination (
                Join-Path (Split-Path -Parent $Executable) 'FFmpeg-GPLv3-LICENSE.txt'
            ) -Force
        }
    }

    if (Test-Path -LiteralPath $ReadmePath -PathType Leaf) {
        Copy-Item -LiteralPath $ReadmePath -Destination (
            Join-Path (Split-Path -Parent $Executable) 'README.md'
        ) -Force
    }

    if (Test-Path -LiteralPath $LicensePath -PathType Leaf) {
        Copy-Item -LiteralPath $LicensePath -Destination (
            Join-Path (Split-Path -Parent $Executable) 'LICENSE.txt'
        ) -Force
    }

    $Hash = (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash
    $Size = (Get-Item -LiteralPath $Executable).Length
    "$Hash *VideoCompressor.exe" | Set-Content -LiteralPath (
        Join-Path (Split-Path -Parent $Executable) 'SHA256SUMS.txt'
    ) -Encoding ASCII
    [pscustomobject]@{
        Mode = $BuildMode
        Executable = $Executable
        Bytes = $Size
        Sha256 = $Hash
    }
}

$Results = [System.Collections.Generic.List[object]]::new()
if ($Mode -in @('Standalone', 'Both')) {
    $Results.Add((Invoke-NuitkaBuild -BuildMode 'Standalone'))
}
if ($Mode -in @('OneFile', 'Both')) {
    $Results.Add((Invoke-NuitkaBuild -BuildMode 'OneFile'))
}

$Results | Format-Table -AutoSize
