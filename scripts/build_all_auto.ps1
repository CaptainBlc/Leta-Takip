# Leta Takip - Otomatik Build Script (Windows)
# Bu script hem Windows build hem de GitHub Actions ile Mac build'i tetikler
# Kullanım: .\scripts\build_all_auto.ps1 -Version 1.3

param(
  [string]$Version = "1.3",
  [switch]$SkipMac = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$versionTag = $Version.Replace(".", "_")

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Leta Takip - Otomatik Build" -ForegroundColor Cyan
Write-Host "  Version: $Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Windows Build
Write-Host "🪟 WINDOWS BUILD BAŞLIYOR..." -ForegroundColor Yellow
Write-Host ""
& "$PSScriptRoot\build_setup.ps1" -Version $Version

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Windows build başarısız!" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "✅ Windows build tamamlandı!" -ForegroundColor Green
Write-Host ""

# 2. Mac Build (GitHub Actions ile)
if (-not $SkipMac) {
  Write-Host "🍎 MAC BUILD (GitHub Actions)..." -ForegroundColor Yellow
  Write-Host ""
  
  # GitHub CLI kontrolü
  if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  GitHub CLI (gh) bulunamadı." -ForegroundColor Yellow
    Write-Host "   Mac build için GitHub Actions kullanılacak." -ForegroundColor Yellow
    Write-Host "   GitHub CLI kurmak için: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Manuel olarak GitHub Actions'ı tetiklemek için:" -ForegroundColor Yellow
    Write-Host "   1. GitHub repo'ya gidin" -ForegroundColor Gray
    Write-Host "   2. Actions sekmesine gidin" -ForegroundColor Gray
    Write-Host "   3. 'Build All Platforms' workflow'unu seçin" -ForegroundColor Gray
    Write-Host "   4. 'Run workflow' butonuna tıklayın" -ForegroundColor Gray
    Write-Host "   5. Version: $Version girin" -ForegroundColor Gray
    Write-Host ""
  } else {
    Write-Host "🚀 GitHub Actions workflow'u tetikleniyor..." -ForegroundColor Cyan
    
    # GitHub Actions workflow'unu tetikle
    gh workflow run "build-all-platforms.yml" -f version="$Version" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
      Write-Host "✅ GitHub Actions workflow'u başlatıldı!" -ForegroundColor Green
      Write-Host ""
      Write-Host "📊 İlerlemeyi görmek için:" -ForegroundColor Cyan
      Write-Host "   gh run list --workflow=build-all-platforms.yml" -ForegroundColor Gray
      Write-Host ""
      Write-Host "📥 Mac build dosyalarını indirmek için:" -ForegroundColor Cyan
      Write-Host "   gh run download --workflow=build-all-platforms.yml" -ForegroundColor Gray
      Write-Host ""
    } else {
      Write-Host "⚠️  GitHub Actions tetiklenemedi." -ForegroundColor Yellow
      Write-Host "   Manuel olarak GitHub Actions'ı tetikleyin." -ForegroundColor Yellow
    }
  }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ TÜM BUILD İŞLEMLERİ TAMAMLANDI!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 Windows dosyaları:" -ForegroundColor Cyan
Write-Host "   • dist\Leta_Pipeline_v${versionTag}.exe" -ForegroundColor White
if (Test-Path "dist\Leta_Takip_Setup_v${versionTag}.exe") {
  Write-Host "   • dist\Leta_Takip_Setup_v${versionTag}.exe" -ForegroundColor White
}
Write-Host ""
Write-Host "🍎 Mac dosyaları GitHub Actions'da oluşturulacak." -ForegroundColor Cyan
Write-Host ""

