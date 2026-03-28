#define MyAppName "Dictly"
#define MyAppPublisher "Dictly Contributors"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef AppSource
  #error AppSource must be passed to the installer compiler.
#endif

[Setup]
AppId={{8A3BA62F-E241-4C89-BC6A-9F1FBB7F4B21}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Dictly
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=installer-dist
OutputBaseFilename=Dictly-Setup
DiskSpanning=yes
DiskSliceSize=2000000000
UninstallDisplayIcon={app}\Dictly.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\Dictly.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Dictly.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Dictly.exe"; Description: "Launch Dictly"; Flags: nowait postinstall skipifsilent
