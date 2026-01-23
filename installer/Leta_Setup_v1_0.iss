[Setup]
AppId={{6A5E4B5A-4C85-4F08-9A3A-0C1C5A8D6A10}}
AppName=Leta Yönetim Paneli
AppVersion=1.0
AppPublisher=Leta Aile ve Çocuk
DefaultDirName={autopf}\LetaYonetim
DefaultGroupName=Leta Yönetim
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
OutputDir=.
OutputBaseFilename=Leta_Yonetim_Setup_v1_0
WizardStyle=modern
UninstallDisplayIcon={app}\Leta_Yonetim_Paneli_v1_0.exe
; Not: SetupIconFile bir .ico bekler. EXE büyük olduğu için "File is too large" hatası verebiliyor.
; İkonu şimdilik default bırakıyoruz. (İstersen logo.png'den .ico üreterek ekleriz.)

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"
Name: "openguide"; Description: "Kurulum bitince kullanım kılavuzunu aç"; GroupDescription: "Ek seçenekler:"; Flags: unchecked

[Files]
Source: "..\dist\Leta_Yonetim_Paneli_v1_0.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\KULLANIM_KILAVUZU.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Leta Yönetim Paneli"; Filename: "{app}\Leta_Yonetim_Paneli_v1_0.exe"
Name: "{group}\Kullanım Kılavuzu"; Filename: "{app}\KULLANIM_KILAVUZU.txt"
Name: "{commondesktop}\Leta Yönetim Paneli"; Filename: "{app}\Leta_Yonetim_Paneli_v1_0.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Leta_Yonetim_Paneli_v1_0.exe"; Description: "Uygulamayı çalıştır"; Flags: nowait postinstall skipifsilent
Filename: "{app}\KULLANIM_KILAVUZU.txt"; Description: "Kullanım kılavuzunu aç"; Tasks: openguide; Flags: postinstall shellexec skipifsilent



