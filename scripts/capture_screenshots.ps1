# 截图脚本（本地开发用）：用 Edge 无头模式导出 demo 各步骤截图
# Screenshot helper: exports each demo step as PNG via headless Edge.
param(
  [string]$DemoRoot = (Join-Path $PSScriptRoot ".."),
  [string]$Edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)
$demo = Join-Path $DemoRoot "demo\index.html"
$outDir = Join-Path $DemoRoot "screenshots"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$tempBase = Join-Path $env:TEMP "edge-demo-shot"
for ($n = 1; $n -le 4; $n++) {
  $out = Join-Path $outDir "demo-step$n.png"
  $ud = "$tempBase-$n-$([guid]::NewGuid().ToString('N'))"
  New-Item -ItemType Directory -Force -Path $ud | Out-Null
  $url = "file:///" + (($demo -replace "\\","/") + "#step=$n&export=1")
  $p = Start-Process -FilePath $Edge -ArgumentList @(
    "--headless","--disable-gpu","--use-angle=swiftshader","--no-sandbox",
    "--disable-dev-shm-usage","--no-first-run","--no-default-browser-check",
    "--disable-extensions","--user-data-dir=$ud","--hide-scrollbars",
    "--screenshot=$out","--window-size=1440,900",$url
  ) -PassThru -Wait -WindowStyle Hidden
  if (Test-Path $out) {
    $kb = [math]::Round((Get-Item $out).Length / 1kb)
    Write-Host "step$n OK (${kb}KB)"
  } else {
    Write-Host "step$n FAIL (exit=$($p.ExitCode))"
  }
  Remove-Item -LiteralPath $ud -Recurse -Force -ErrorAction SilentlyContinue
}
