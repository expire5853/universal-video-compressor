<#
.SYNOPSIS
Compress a video to H.265/HEVC with the AMD AMF hardware encoder.

.DESCRIPTION
Provides several presets for low-motion screen and operation demonstrations.
The script keeps the source resolution, reduces frame rate according to the
selected preset, copies audio by default, prevents accidental overwrite, and
uses ffprobe to verify the completed output.

.EXAMPLE
.\Compress-Video.ps1 -ListPresets

.EXAMPLE
.\Compress-Video.ps1 -InputPath 'C:\Videos\demo.mp4' -Preset Quality

.EXAMPLE
.\Compress-Video.ps1 -InputPath 'C:\Videos\demo.mp4' -Preset Compact -FrameRate 24 -Hash

.EXAMPLE
.\Compress-Video.ps1 -InputPath 'C:\Videos\demo.mp4' -Preset Quality -DryRun
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$InputPath,

    [ValidateSet('Quality', 'Compact', 'Tiny', 'Fast')]
    [string]$Preset = 'Quality',

    [string]$OutputPath,

    [ValidateRange(1, 240)]
    [int]$FrameRate,

    [ValidateSet('Copy', 'AAC128')]
    [string]$AudioMode = 'Copy',

    [string]$FfmpegPath,

    [switch]$Overwrite,

    [switch]$DryRun,

    [switch]$Hash,

    [switch]$ListPresets
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$presetDefinitions = [ordered]@{
    Quality = [pscustomobject]@{
        Description  = 'Highest effective AMF quality for UI text and fine lines.'
        FrameRate    = 30
        Qvbr          = 45
        Usage         = 'high_quality'
        Quality       = 'quality'
        FullAnalysis  = $true
        GopSeconds    = 10
    }
    Compact = [pscustomobject]@{
        Description  = 'High visual quality with a smaller output than Quality.'
        FrameRate    = 30
        Qvbr          = 40
        Usage         = 'high_quality'
        Quality       = 'quality'
        FullAnalysis  = $true
        GopSeconds    = 10
    }
    Tiny = [pscustomobject]@{
        Description  = 'Smallest output for mostly static operation demos.'
        FrameRate    = 24
        Qvbr          = 30
        Usage         = 'high_quality'
        Quality       = 'quality'
        FullAnalysis  = $true
        GopSeconds    = 10
    }
    Fast = [pscustomobject]@{
        Description  = 'Faster GPU encoding with reduced lookahead analysis.'
        FrameRate    = 30
        Qvbr          = 40
        Usage         = 'transcoding'
        Quality       = 'balanced'
        FullAnalysis  = $false
        GopSeconds    = 4
    }
}

function Show-PresetTable {
    $presetDefinitions.GetEnumerator() | ForEach-Object {
        [pscustomobject]@{
            Preset       = $_.Key
            FPS          = $_.Value.FrameRate
            QVBR         = $_.Value.Qvbr
            Analysis     = if ($_.Value.FullAnalysis) { 'Full' } else { 'Reduced' }
            Description  = $_.Value.Description
        }
    } | Format-Table -AutoSize
}

function Resolve-FfmpegExecutable {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        $explicitItem = Get-Item -LiteralPath $ExplicitPath -ErrorAction Stop
        if ($explicitItem.PSIsContainer -or $explicitItem.Name -ne 'ffmpeg.exe') {
            throw "-FfmpegPath must point to ffmpeg.exe: $ExplicitPath"
        }
        return $explicitItem.FullName
    }

    $command = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $wingetPackages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (Test-Path -LiteralPath $wingetPackages) {
        $candidates = Get-ChildItem -LiteralPath $wingetPackages -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like 'Gyan.FFmpeg_*' } |
            ForEach-Object {
                Get-ChildItem -LiteralPath $_.FullName -Recurse -File -Filter ffmpeg.exe -ErrorAction SilentlyContinue
            } |
            Sort-Object LastWriteTime -Descending

        $candidate = $candidates | Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    throw 'ffmpeg.exe was not found in PATH or the WinGet Gyan.FFmpeg package directory.'
}

function Resolve-FfprobeExecutable {
    param([string]$ResolvedFfmpegPath)

    $siblingPath = Join-Path (Split-Path -Parent $ResolvedFfmpegPath) 'ffprobe.exe'
    if (Test-Path -LiteralPath $siblingPath) {
        return (Get-Item -LiteralPath $siblingPath).FullName
    }

    $command = Get-Command ffprobe.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw 'ffprobe.exe was not found next to ffmpeg.exe or in PATH.'
}

function Format-CommandArgument {
    param([string]$Argument)

    if ($Argument -notmatch '[\s"]') {
        return $Argument
    }

    return '"' + ($Argument -replace '"', '\"') + '"'
}

if ($ListPresets) {
    Show-PresetTable
    return
}

if (-not $InputPath) {
    throw 'Specify -InputPath, or use -ListPresets.'
}

$inputItem = Get-Item -LiteralPath $InputPath -ErrorAction Stop
if ($inputItem.PSIsContainer) {
    throw "InputPath must be a video file: $InputPath"
}

$selectedPreset = $presetDefinitions[$Preset]
$effectiveFrameRate = if ($PSBoundParameters.ContainsKey('FrameRate')) {
    $FrameRate
} else {
    $selectedPreset.FrameRate
}

$resolvedFfmpegPath = Resolve-FfmpegExecutable -ExplicitPath $FfmpegPath
$resolvedFfprobePath = Resolve-FfprobeExecutable -ResolvedFfmpegPath $resolvedFfmpegPath

$encoderOutput = & $resolvedFfmpegPath -hide_banner -encoders 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $encoderOutput -notmatch '\bhevc_amf\b') {
    throw "The selected FFmpeg build does not expose the AMD hevc_amf encoder: $resolvedFfmpegPath"
}

if ($OutputPath) {
    $resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
} else {
    $outputName = '{0}_H265_AMF_{1}_{2}fps.mp4' -f @(
        [System.IO.Path]::GetFileNameWithoutExtension($inputItem.Name),
        $Preset.ToUpperInvariant(),
        $effectiveFrameRate
    )
    $resolvedOutputPath = Join-Path $inputItem.DirectoryName $outputName
}

$outputDirectory = Split-Path -Parent $resolvedOutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    throw "Output directory does not exist: $outputDirectory"
}

if ([string]::Equals($inputItem.FullName, $resolvedOutputPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Input and output paths must be different.'
}

if ((Test-Path -LiteralPath $resolvedOutputPath) -and -not $Overwrite) {
    throw "Output already exists. Use -Overwrite to replace it: $resolvedOutputPath"
}

$gopSize = $effectiveFrameRate * $selectedPreset.GopSeconds
$ffmpegArguments = @(
    '-hide_banner',
    '-loglevel', 'warning',
    '-nostdin'
)

if ($Overwrite) {
    $ffmpegArguments += '-y'
} else {
    $ffmpegArguments += '-n'
}

$ffmpegArguments += @(
    '-i', $inputItem.FullName,
    '-map', '0:v:0',
    '-map', '0:a?',
    '-map_metadata', '0',
    '-vf', "fps=$effectiveFrameRate",
    '-c:v', 'hevc_amf',
    '-usage', $selectedPreset.Usage,
    '-quality', $selectedPreset.Quality,
    '-rc', 'qvbr',
    '-qvbr_quality_level', [string]$selectedPreset.Qvbr,
    '-g', [string]$gopSize,
    '-pix_fmt', 'yuv420p',
    '-tag:v', 'hvc1'
)

if ($selectedPreset.FullAnalysis) {
    $ffmpegArguments += @(
        '-async_depth', '42',
        '-vbaq', 'true',
        '-preencode', 'true',
        '-high_motion_quality_boost_enable', 'true',
        '-preanalysis', 'true',
        '-pa_activity_type', 'yuv',
        '-pa_scene_change_detection_enable', 'true',
        '-pa_scene_change_detection_sensitivity', 'high',
        '-pa_static_scene_detection_enable', 'true',
        '-pa_static_scene_detection_sensitivity', 'high',
        '-pa_caq_strength', 'high',
        '-pa_frame_sad_enable', 'true',
        '-pa_lookahead_buffer_depth', '41',
        '-pa_paq_mode', 'caq',
        '-pa_taq_mode', '2',
        '-pa_high_motion_quality_boost_mode', 'auto'
    )
}

if ($AudioMode -eq 'Copy') {
    $ffmpegArguments += @('-c:a', 'copy')
} else {
    $ffmpegArguments += @('-c:a', 'aac', '-b:a', '128k')
}

$metadataComment = 'AMD AMF HEVC preset={0}; QVBR={1}; fps={2}' -f @(
    $Preset,
    $selectedPreset.Qvbr,
    $effectiveFrameRate
)

$ffmpegArguments += @(
    '-metadata', "comment=$metadataComment",
    '-movflags', '+faststart',
    '-stats',
    $resolvedOutputPath
)

Write-Host ('Preset : {0} ({1})' -f $Preset, $selectedPreset.Description)
Write-Host ('Input  : {0}' -f $inputItem.FullName)
Write-Host ('Output : {0}' -f $resolvedOutputPath)
Write-Host ('Video  : HEVC/AMF, {0} fps, QVBR {1}' -f $effectiveFrameRate, $selectedPreset.Qvbr)
Write-Host ('Audio  : {0}' -f $AudioMode)

if ($DryRun) {
    $displayArguments = $ffmpegArguments | ForEach-Object { Format-CommandArgument -Argument ([string]$_) }
    Write-Host ''
    Write-Host 'Dry run; no output was written:'
    Write-Host ((Format-CommandArgument -Argument $resolvedFfmpegPath) + ' ' + ($displayArguments -join ' '))
    return
}

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
& $resolvedFfmpegPath @ffmpegArguments
$encodeExitCode = $LASTEXITCODE
$stopwatch.Stop()

if ($encodeExitCode -ne 0) {
    throw "FFmpeg failed with exit code $encodeExitCode. Any partial output should not be treated as complete."
}

$ffprobeArguments = @(
    '-v', 'error',
    '-show_entries', 'stream=index,codec_type,codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,bit_rate,duration,nb_frames,sample_rate,channels:format=duration,size,bit_rate',
    '-of', 'json',
    $resolvedOutputPath
)
$probeJson = & $resolvedFfprobePath @ffprobeArguments

if ($LASTEXITCODE -ne 0) {
    throw "ffprobe could not verify the completed output: $resolvedOutputPath"
}

$probe = ($probeJson | Out-String) | ConvertFrom-Json
$videoStream = @($probe.streams) | Where-Object { $_.codec_type -eq 'video' } | Select-Object -First 1
if (-not $videoStream -or $videoStream.codec_name -ne 'hevc') {
    throw "Verification failed: the output video stream is not HEVC: $resolvedOutputPath"
}

$outputItem = Get-Item -LiteralPath $resolvedOutputPath
$reductionPercent = [math]::Round((1 - ($outputItem.Length / $inputItem.Length)) * 100, 2)

$result = [pscustomobject]@{
    OutputPath        = $outputItem.FullName
    Preset            = $Preset
    Codec             = $videoStream.codec_name
    Profile           = $videoStream.profile
    Resolution        = '{0}x{1}' -f $videoStream.width, $videoStream.height
    FrameRate         = $videoStream.avg_frame_rate
    DurationSeconds   = [math]::Round([double]$probe.format.duration, 3)
    OutputMiB         = [math]::Round($outputItem.Length / 1MB, 3)
    ReductionPercent  = $reductionPercent
    EncodeSeconds     = [math]::Round($stopwatch.Elapsed.TotalSeconds, 2)
}

if ($Hash) {
    $result | Add-Member -NotePropertyName SHA256 -NotePropertyValue (
        (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedOutputPath).Hash
    )
}

Write-Host ''
Write-Host 'Compression completed and ffprobe verification passed.'
$result | Format-List
