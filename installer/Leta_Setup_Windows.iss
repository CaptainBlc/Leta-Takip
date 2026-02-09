[Setup]
AppId={{6A5E4B5A-4C85-4F08-9A3A-0C1C5A8D6A10}}
AppName=Leta Takip
AppVersion=1.3
AppPublisher=Leta Aile ve Çocuk
DefaultDirName={autopf}\LetaTakip
DefaultGroupName=Leta Takip
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist
OutputBaseFilename=Leta_Takip_Setup_v1_3
WizardStyle=modern
UninstallDisplayIcon={app}\Leta_Pipeline_v1_3.exe
; Kılavuz: script/assets veya repo kökü (CI'da script/assets kullanılır)
LicenseFile=..\script\assets\KULLANIM_KILAVUZU.txt
InfoBeforeFile=..\script\assets\KULLANIM_KILAVUZU.txt

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Hızlı başlatma çubuğuna ekle"; GroupDescription: "Kısayollar:"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "openguide"; Description: "Kurulum bitince kullanım kılavuzunu aç"; GroupDescription: "Ek seçenekler:"; Flags: unchecked

[Files]
Source: "..\dist\Leta_Pipeline_v1_3.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\script\assets\KULLANIM_KILAVUZU.txt"; DestDir: "{app}"; DestName: "KULLANIM_KILAVUZU.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\Leta Takip"; Filename: "{app}\Leta_Pipeline_v1_3.exe"
Name: "{group}\Kullanım Kılavuzu"; Filename: "{app}\KULLANIM_KILAVUZU.txt"
Name: "{group}\Leta Takip'i Kaldır"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Leta Takip"; Filename: "{app}\Leta_Pipeline_v1_3.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Leta Takip"; Filename: "{app}\Leta_Pipeline_v1_3.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\Leta_Pipeline_v1_3.exe"; Description: "Uygulamayı çalıştır"; Flags: nowait postinstall skipifsilent
Filename: "{app}\KULLANIM_KILAVUZU.txt"; Description: "Kullanım kılavuzunu aç"; Tasks: openguide; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backups"
Type: filesandordirs; Name: "{app}\*.db"

[Code]
procedure InitializeWizard;
begin
  // LicenseFile ve InfoBeforeFile otomatik yüklenir
  // Başlık değiştirmek isterseniz:
  WizardForm.LicenseLabel1.Caption := 'Leta Takip v1.3 - Kullanım Kılavuzu';
end;

