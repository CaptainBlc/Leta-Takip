param(
  [string]$Version = "1.0"
)

$ErrorActionPreference = "Stop"

# Script hangi klasörden çağrılırsa çağrılsın repo root'ta çalış
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "== Leta build & setup (v$Version) ==" -ForegroundColor Cyan

Write-Host "1) Building EXE with PyInstaller..." -ForegroundColor Yellow
# Dist kilitlenme sorunlarına karşı önce geçici klasöre build al, sonra dist'e kopyala
$distTmp = "dist_build"
$buildTmp = "build_build"
$distFinal = "dist"
$exeName = "Leta_Yonetim_Paneli_v1_0.exe"

if (Test-Path $distTmp) { Remove-Item -Recurse -Force $distTmp -ErrorAction SilentlyContinue }
if (Test-Path $buildTmp) { Remove-Item -Recurse -Force $buildTmp -ErrorAction SilentlyContinue }

pyinstaller --clean --noconfirm --onefile --windowed --name "Leta_Yonetim_Paneli_v1_0" --add-data "KULLANIM_KILAVUZU.txt;." --distpath $distTmp --workpath $buildTmp "leta_app.py"                   

if (-not (Test-Path $distFinal)) { New-Item -ItemType Directory -Path $distFinal | Out-Null }
if (Test-Path (Join-Path $distFinal $exeName)) { Remove-Item -Force (Join-Path $distFinal $exeName) -ErrorAction SilentlyContinue }
Copy-Item -Force (Join-Path $distTmp $exeName) (Join-Path $distFinal $exeName)

Write-Host "2) Building installer with Inno Setup (iscc.exe)..." -ForegroundColor Yellow
$iscc = $null
try {
  $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source) { $iscc = $cmd.Source }
} catch { }
if (-not $iscc) {
  $common = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
  if (Test-Path $common) { $iscc = $common }
}

if (-not $iscc) {
  Write-Host "Inno Setup bulunamadı." -ForegroundColor Red
  Write-Host "Kurulum: Inno Setup 6 yükleyin, sonra tekrar çalıştırın." -ForegroundColor Red
  Write-Host "ISS dosyası: installer\\Leta_Setup_v1_0.iss" -ForegroundColor Red
  exit 1
}

& $iscc "installer\\Leta_Setup_v1_0.iss"
Write-Host "OK -> installer\\Leta_Yonetim_Setup_v1_0.exe" -ForegroundColor Green



