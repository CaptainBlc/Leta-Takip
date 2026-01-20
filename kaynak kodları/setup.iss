; Inno Setup Script - Leta Yönetim Sistemi
; Bu dosyayı Inno Setup Compiler ile derleyin

[Setup]
AppName=Leta Yönetim Sistemi
AppVersion=4.0
AppPublisher=Leta Aile ve Çocuk
AppPublisherURL=
DefaultDirName={autopf}\Leta Yönetim
DefaultGroupName=Leta Yönetim
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=installer
OutputBaseFilename=Leta_Yonetim_Setup_v4.0
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\Leta_Yonetim_Final.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\leta_data.db"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Dirs]
Name: "{app}\Yedekler"; Flags: uninsalwaysuninstall

[Icons]
Name: "{group}\Leta Yönetim Sistemi"; Filename: "{app}\Leta_Yonetim_Final.exe"
Name: "{group}\{cm:UninstallProgram,Leta Yönetim Sistemi}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Leta Yönetim Sistemi"; Filename: "{app}\Leta_Yonetim_Final.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Leta Yönetim Sistemi"; Filename: "{app}\Leta_Yonetim_Final.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\Leta_Yonetim_Final.exe"; Description: "{cm:LaunchProgram,Leta Yönetim Sistemi}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel1.Caption := 'Leta Yönetim Sistemi Kurulumuna Hoş Geldiniz';
  WizardForm.WelcomeLabel2.Caption := 'Bu sihirbaz, Leta Yönetim Sistemini bilgisayarınıza kuracaktır.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Yedekler klasörünü oluştur (eğer yoksa)
    if not DirExists(ExpandConstant('{app}\Yedekler')) then
      CreateDir(ExpandConstant('{app}\Yedekler'));
  end;
end;

