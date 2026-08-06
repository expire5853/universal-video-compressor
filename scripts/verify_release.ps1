[CmdletBinding()]
param(
    [string]$ArtifactRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ArtifactRoot = if ($ArtifactRoot) {
    [System.IO.Path]::GetFullPath($ArtifactRoot)
}
else {
    Join-Path $ProjectRoot 'artifacts'
}
$ReleaseRoot = Join-Path $ArtifactRoot 'release'

if (-not (Test-Path -LiteralPath $ReleaseRoot -PathType Container)) {
    throw "Release directory not found: $ReleaseRoot"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

$ZipExpectations = [ordered]@{
    'Universal-Video-Compressor-Windows-Full.zip' = @(
        'VideoCompressor-Full.exe'
        'README.md'
        'README.zh-CN.md'
        'LICENSE.txt'
        'THIRD_PARTY_NOTICES.md'
        'FFmpeg-GPLv3-LICENSE.txt'
        'SHA256SUMS.txt'
    )
    'Universal-Video-Compressor-Windows-Lite.zip' = @(
        'VideoCompressor-Lite.exe'
        'README.md'
        'README.zh-CN.md'
        'LICENSE.txt'
        'THIRD_PARTY_NOTICES.md'
        'SHA256SUMS.txt'
    )
}

$ArchiveResults = foreach ($ZipName in $ZipExpectations.Keys) {
    $ZipPath = Join-Path $ReleaseRoot $ZipName
    if (-not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) {
        throw "Release archive not found: $ZipPath"
    }

    $Archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $Entries = @($Archive.Entries | ForEach-Object FullName)
        $Missing = @($ZipExpectations[$ZipName] | Where-Object { $_ -notin $Entries })
        if ($Missing) {
            throw "$ZipName is missing: $($Missing -join ', ')"
        }
        if (
            $ZipName -like '*Lite*' -and
            'FFmpeg-GPLv3-LICENSE.txt' -in $Entries
        ) {
            throw 'The Lite archive unexpectedly contains the FFmpeg license.'
        }

        [pscustomobject]@{
            Archive = $ZipName
            Entries = $Entries.Count
            Bytes = (Get-Item -LiteralPath $ZipPath).Length
        }
    }
    finally {
        $Archive.Dispose()
    }
}

$ExpectedChecksumFiles = @(
    'Universal-Video-Compressor-Windows-Full.zip'
    'Universal-Video-Compressor-Windows-Lite.zip'
    'VideoCompressor-Full.exe'
    'VideoCompressor-Lite.exe'
)
$ChecksumPath = Join-Path $ReleaseRoot 'SHA256SUMS.txt'
$ChecksumLines = @(Get-Content -LiteralPath $ChecksumPath -Encoding ASCII)
if ($ChecksumLines.Count -ne $ExpectedChecksumFiles.Count) {
    throw (
        "Expected $($ExpectedChecksumFiles.Count) release checksums, " +
        "found $($ChecksumLines.Count)."
    )
}

$CheckedNames = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)
foreach ($Line in $ChecksumLines) {
    if ($Line -notmatch '^(?<hash>[0-9A-F]{64}) \*(?<name>.+)$') {
        throw "Invalid checksum line: $Line"
    }
    $ExpectedHash = $Matches['hash']
    $Name = $Matches['name']
    if (-not $CheckedNames.Add($Name)) {
        throw "Duplicate checksum entry: $Name"
    }
    $AssetPath = Join-Path $ReleaseRoot $Name
    if (-not (Test-Path -LiteralPath $AssetPath -PathType Leaf)) {
        throw "Checksummed asset not found: $AssetPath"
    }
    $ActualHash = (Get-FileHash -LiteralPath $AssetPath -Algorithm SHA256).Hash
    if ($ActualHash -ne $ExpectedHash) {
        throw "Checksum mismatch: $Name"
    }
}
foreach ($ExpectedName in $ExpectedChecksumFiles) {
    if (-not $CheckedNames.Contains($ExpectedName)) {
        throw "Release checksum is missing: $ExpectedName"
    }
}

$Builds = @(
    [pscustomobject]@{
        Edition = 'Full'
        Executable = Join-Path $ArtifactRoot 'full\onefile\VideoCompressor-Full.exe'
        Bundled = $true
        Language = 'en'
    }
    [pscustomobject]@{
        Edition = 'Lite'
        Executable = Join-Path $ArtifactRoot 'lite\onefile\VideoCompressor-Lite.exe'
        Bundled = $false
        Language = 'zh_CN'
    }
)

$ExecutableResults = foreach ($Build in $Builds) {
    if (-not (Test-Path -LiteralPath $Build.Executable -PathType Leaf)) {
        throw "$($Build.Edition) executable not found: $($Build.Executable)"
    }
    $Diagnostics = Join-Path (
        [System.IO.Path]::GetTempPath()
    ) "uvc-$($Build.Edition)-$([guid]::NewGuid().ToString('N')).json"
    try {
        $Arguments = (
            "--language $($Build.Language) " +
            "--diagnostics-report=`"$Diagnostics`" --self-test"
        )
        $ProcessArguments = @{
            FilePath = $Build.Executable
            ArgumentList = $Arguments
            WindowStyle = 'Hidden'
            Wait = $true
            PassThru = $true
        }
        $Process = Start-Process @ProcessArguments
        if ($Process.ExitCode -ne 0) {
            throw (
                "$($Build.Edition) self-test failed with exit code " +
                "$($Process.ExitCode)."
            )
        }
        if (-not (Test-Path -LiteralPath $Diagnostics -PathType Leaf)) {
            throw "$($Build.Edition) self-test produced no diagnostics."
        }

        $Report = Get-Content -LiteralPath $Diagnostics -Raw -Encoding UTF8 |
            ConvertFrom-Json
        $ErrorProperty = $Report.PSObject.Properties['error']
        if ($ErrorProperty -and $ErrorProperty.Value) {
            throw "$($Build.Edition) diagnostics failed: $($ErrorProperty.Value)"
        }
        if ([bool]$Report.resolved_tools.bundled -ne $Build.Bundled) {
            throw "$($Build.Edition) resolved the wrong FFmpeg source."
        }
        if ($Report.language -ne $Build.Language) {
            throw "$($Build.Edition) did not use $($Build.Language)."
        }

        [pscustomobject]@{
            Edition = $Build.Edition
            Language = $Report.language
            BundledFfmpeg = [bool]$Report.resolved_tools.bundled
            Backends = $Report.capabilities.backends.Count
        }
    }
    finally {
        if (Test-Path -LiteralPath $Diagnostics -PathType Leaf) {
            Remove-Item -LiteralPath $Diagnostics -Force
        }
    }
}

$ArchiveResults | Format-Table -AutoSize
$ExecutableResults | Format-Table -AutoSize
Write-Host "Verified $($ChecksumLines.Count) release checksums."
