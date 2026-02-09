#ifndef AppVersion
  #define AppVersion "1.3"
#endif

#define VersionUnderscore StringChange(AppVersion, ".", "_")
#define ExeName "Leta_Pipeline_v" + VersionUnderscore + ".exe"
#define SetupFileName "Leta_Takip_Setup_v" + VersionUnderscore

[Setup]
AppId={{6A5E4B5A-4C85-4F08-9A3A-0C1C5A8D6A10}}
AppName=Leta Takip
AppVersion={#AppVersion}
AppPublisher=Leta Aile ve Çocuk
DefaultDirName={autopf}\LetaTakip
DefaultGroupName=Leta Takip
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist
OutputBaseFilename={#SetupFileName}
WizardStyle=modern
UninstallDisplayIcon={app}\{#ExeName}
LicenseFile=..\KULLANIM_KILAVUZU.txt
InfoBeforeFile=..\KULLANIM_KILAVUZU.txt

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Hızlı başlatma çubuğuna ekle"; GroupDescription: "Kısayollar:"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "openguide"; Description: "Kurulum bitince kullanım kılavuzunu aç"; GroupDescription: "Ek seçenekler:"; Flags: unchecked

[Files]
Source: "..\dist\{#ExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\KULLANIM_KILAVUZU.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Leta Takip"; Filename: "{app}\{#ExeName}"
Name: "{group}\Kullanım Kılavuzu"; Filename: "{app}\KULLANIM_KILAVUZU.txt"
Name: "{group}\Leta Takip'i Kaldır"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Leta Takip"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Leta Takip"; Filename: "{app}\{#ExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Uygulamayı çalıştır"; Flags: nowait postinstall skipifsilent
Filename: "{app}\KULLANIM_KILAVUZU.txt"; Description: "Kullanım kılavuzunu aç"; Tasks: openguide; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backups"
Type: filesandordirs; Name: "{app}\*.db"

[Code]
procedure InitializeWizard;
begin
  // LicenseFile ve InfoBeforeFile otomatik yüklenir
  // Başlık değiştirmek isterseniz:
  WizardForm.LicenseLabel1.Caption := 'Leta Takip v{#AppVersion} - Kullanım Kılavuzu';
end;

