; Inno Setup script for jp2a Studio.
; Built in CI against the PyInstaller onedir output at dist\jp2a-studio\*
; (which by then also contains the cross-compiled jp2a.exe + its DLLs).
; Compile with: iscc packaging\windows\installer.iss
; The /DAppVersion=1.0.0 define is passed in from CI.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define AppName "jp2a Studio"
#define AppExe "jp2a-studio.exe"
#define DistDir "..\..\dist\jp2a-studio"

[Setup]
AppId={{508132EA-4001-4B20-BC76-435153B73BC1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=jp2a Studio
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=..\..\dist
OutputBaseFilename=jp2a-studio-{#AppVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\..\assets\icon.ico
DisableProgramGroupPage=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent
