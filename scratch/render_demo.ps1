param([switch]$Publish)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$output = Join-Path $root 'artifacts/video-correction-20261021'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$original = Join-Path $output 'original-walkthrough.mp4'
if (-not (Test-Path -LiteralPath $original)) {
    Copy-Item -LiteralPath 'recordings/benchproof_demo_walkthrough.mp4' -Destination $original
}
& (Join-Path $PSScriptRoot 'generate_voiceover.ps1')
$names = @('intro', 'intake', 'plan', 'exec', 'diff', 'bundle', 'customization')
$durations = @(24.824, 20.986, 18.051, 23.530, 16.211, 19.676, 15.000)
$normalized = @()
for ($index = 0; $index -lt $names.Length; $index++) {
    $inputAudio = "recordings/scene$($index + 1)_$($names[$index]).wav"
    $measured = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $inputAudio
    if ($LASTEXITCODE -ne 0) { throw 'Audio duration inspection failed' }
    $tempo = [double]::Parse($measured, [Globalization.CultureInfo]::InvariantCulture) / $durations[$index]
    if ($tempo -lt 0.5 -or $tempo -gt 2) { throw 'Narration requires an unreasonable speed adjustment' }
    $tempoText = $tempo.ToString('F6', [Globalization.CultureInfo]::InvariantCulture)
    $durationText = $durations[$index].ToString('F3', [Globalization.CultureInfo]::InvariantCulture)
    $destination = Join-Path $output "audio-$index.wav"
    & ffmpeg -hide_banner -loglevel error -y -i $inputAudio -af "atempo=$tempoText,apad" -t $durationText -ar 48000 -ac 2 $destination
    if ($LASTEXITCODE -ne 0) { throw 'Narration normalization failed' }
    $normalized += $destination
}
$concat = Join-Path $output 'audio-concat.txt'
($normalized | ForEach-Object { "file '$($_.Replace('\', '/'))'" }) | Set-Content -LiteralPath $concat -Encoding ascii
& ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concat -c:a pcm_s16le recordings/full_voiceover.wav
if ($LASTEXITCODE -ne 0) { throw 'Narration concatenation failed' }
$screenshot = Join-Path $root 'artifacts/coding/customization-20261017/same-task-live-continuation-1792588615820/review-ready-desktop.png'
if (-not (Test-Path -LiteralPath $screenshot)) { throw 'Required dated live-task screenshot is missing' }
$filters = '[0:v]fps=25,setsar=1,tpad=stop_mode=clone:stop_duration=0.158,trim=duration=123.278,setpts=PTS-STARTPTS[base];[1:v]crop=1425:1050:0:0,scale=-2:670,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0xf2f5f7,fps=25,setsar=1,trim=duration=15,setpts=PTS-STARTPTS[still];[base][still]concat=n=2:v=1:a=0[video]'
$result = Join-Path $output 'benchproof_demo_walkthrough.mp4'
& ffmpeg -hide_banner -loglevel error -y -i $original -loop 1 -i $screenshot -i recordings/full_voiceover.wav -i recordings/subtitles.srt -filter_complex $filters -map '[video]' -map 2:a:0 -map 3:s:0 -c:v libx264 -preset fast -crf 21 -pix_fmt yuv420p -c:a aac -b:a 192k -c:s mov_text -t 138.278 -movflags +faststart $result
if ($LASTEXITCODE -ne 0) { throw 'Corrected video render failed' }
& ffmpeg -hide_banner -loglevel error -y -ss 130 -i $result -frames:v 1 recordings/frame_scene7.png
if ($LASTEXITCODE -ne 0) { throw 'Final-scene inspection frame failed' }
& ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,codec_type,width,height,duration -of json $result
if ($LASTEXITCODE -ne 0) { throw 'Corrected video inspection failed' }
if ($Publish) {
    Copy-Item -LiteralPath $result -Destination (Join-Path $root 'recordings/benchproof_demo_walkthrough.mp4')
}
