@echo off
echo ========================================
echo Leta Yonetim Sistemi - Setup Olusturma
echo ========================================
echo.

REM PyInstaller ile EXE oluştur
echo [1/3] EXE dosyasi olusturuluyor...
pyinstaller --clean Leta_Yonetim_Final.spec
if errorlevel 1 (
    echo HATA: EXE olusturulamadi!
    pause
    exit /b 1
)

REM Yedekler klasörünü oluştur (eğer yoksa)
if not exist "dist\Yedekler" mkdir "dist\Yedekler"

REM Veritabanı dosyasını kopyala (eğer yoksa)
if not exist "dist\leta_data.db" (
    echo Veritabani dosyasi olusturuluyor...
    REM Boş bir veritabanı oluşturulacak, program ilk açılışta otomatik oluşturur
)

echo.
echo [2/3] EXE dosyasi basariyla olusturuldu!
echo.

REM Inno Setup ile installer oluştur
echo [3/3] Setup dosyasi olusturuluyor...
echo.
echo NOT: Inno Setup Compiler yuklu degilse, setup.iss dosyasini manuel olarak derleyin.
echo      Inno Setup Compiler: https://jrsoftware.org/isdl.php
echo.

REM Inno Setup Compiler yolunu kontrol et
set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "%INNO_PATH%" (
    "%INNO_PATH%" "setup.iss"
    if errorlevel 1 (
        echo HATA: Setup dosyasi olusturulamadi!
        pause
        exit /b 1
    )
    echo.
    echo [TAMAMLANDI] Setup dosyasi installer klasorunde olusturuldu!
) else (
    echo.
    echo UYARI: Inno Setup Compiler bulunamadi.
    echo        Lutfen setup.iss dosyasini manuel olarak derleyin.
    echo        Veya Inno Setup Compiler'i yukleyin: https://jrsoftware.org/isdl.php
    echo.
    echo EXE dosyasi dist klasorunde hazir.
    echo Setup dosyasi olusturmak icin setup.iss dosyasini Inno Setup ile acin.
)

echo.
pause

