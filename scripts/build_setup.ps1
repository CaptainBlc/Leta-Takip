param(
  [string]$Version = "1.3"
)

$ErrorActionPreference = "Stop"

# Script hangi klasörden çağrılırsa çağrılsın repo root'ta çalış
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$versionTag = $Version.Replace(".", "_")
$exeNameTarget = "Leta_Pipeline_v${versionTag}.exe"
$setupNameTarget = "Leta_Takip_Setup_v${versionTag}.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Leta Takip Build & Setup (v$Version)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1) Building EXE with PyInstaller..." -ForegroundColor Yellow

# EXE dosyası açıksa kapat
$exePath = Join-Path "dist" $exeNameTarget
if (Test-Path $exePath) {
    Write-Host "   Mevcut EXE kontrol ediliyor..." -ForegroundColor Gray
    $processes = Get-Process | Where-Object { $_.Path -like "*Leta_Pipeline_v1_3.exe*" }
    if ($processes) {
        Write-Host "   ⚠️  EXE çalışıyor, kapatılıyor..." -ForegroundColor Yellow
        $processes | Stop-Process -Force
        Start-Sleep -Seconds 2
    }
    Write-Host "   🗑️  Eski EXE siliniyor..." -ForegroundColor Gray
    Remove-Item $exePath -Force -ErrorAction SilentlyContinue
}

# Dist kilitlenme sorunlarına karşı önce geçici klasöre build al, sonra dist'e kopyala
$distTmp = "dist_build"
$buildTmp = "build_build"
$distFinal = "dist"
$exeName = $exeNameTarget

if (Test-Path $distTmp) { Remove-Item -Recurse -Force $distTmp -ErrorAction SilentlyContinue }
if (Test-Path $buildTmp) { Remove-Item -Recurse -Force $buildTmp -ErrorAction SilentlyContinue }

Write-Host "   PyInstaller çalışıyor... (2-3 dakika sürebilir)" -ForegroundColor Gray
pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec

$builtExe = Get-ChildItem -Path $distFinal -Filter "Leta_Pipeline_v*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $builtExe) {
  Write-Host "❌ HATA: EXE dosyası oluşturulamadı!" -ForegroundColor Red
  exit 1
}
if ($builtExe.Name -ne $exeNameTarget) {
  Copy-Item $builtExe.FullName (Join-Path $distFinal $exeNameTarget) -Force
}
$exeName = $exeNameTarget

Write-Host "✅ EXE oluşturuldu: dist\$exeName" -ForegroundColor Green
Write-Host ""

Write-Host "2) Building installer with Inno Setup..." -ForegroundColor Yellow
$iscc = $null
try {
  $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
} catch { }

if (-not $iscc) {
  $common = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
  if (Test-Path $common) { $iscc = $common }
}

if (-not $iscc) {
  Write-Host "⚠️  UYARI: Inno Setup bulunamadı." -ForegroundColor Yellow
  Write-Host "   Setup dosyası oluşturulamadı, ancak EXE hazır." -ForegroundColor Yellow
  Write-Host "   Inno Setup kurmak için: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
  Write-Host "   Setup dosyasını manuel oluşturmak için:" -ForegroundColor Yellow
  Write-Host "   `"$common`" installer\Leta_Setup_Windows.iss" -ForegroundColor Gray
  Write-Host ""
  Write-Host "✅ Build tamamlandı! (EXE hazır)" -ForegroundColor Green
  exit 0
}

Write-Host "   Inno Setup ile setup dosyası oluşturuluyor..." -ForegroundColor Gray
& $iscc "/DAppVersion=$Version" "installer\Leta_Setup_Windows.iss"

$builtSetup = Get-ChildItem -Path dist -Filter "Leta_Takip_Setup_v*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($builtSetup -and $builtSetup.Name -ne $setupNameTarget) {
  Copy-Item $builtSetup.FullName (Join-Path "dist" $setupNameTarget) -Force
}

if (Test-Path (Join-Path "dist" $setupNameTarget)) {
  Write-Host "✅ Setup dosyası oluşturuldu: dist\$setupNameTarget" -ForegroundColor Green
} else {
  Write-Host "⚠️  Setup dosyası oluşturulamadı, ancak EXE hazır." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ BUILD TAMAMLANDI!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Dosyalar:" -ForegroundColor Cyan
Write-Host "   - dist\$exeName" -ForegroundColor White
if (Test-Path (Join-Path dist $setupNameTarget)) {
  Write-Host "   - dist\$setupNameTarget" -ForegroundColor White
}
Write-Host ""
