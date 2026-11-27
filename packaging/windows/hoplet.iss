; Inno Setup script for Hoplet-Setup.exe. Built by .github/workflows/apps.yml:
;   iscc /DAppVersion=0.1.0 /DSourceDir=..\..\dist\Hoplet packaging\windows\hoplet.iss
; Installs for the current user only (no admin prompt).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\Hoplet"
#endif

[Setup]
AppId={{6F0C4B7E-8D3A-4B57-9E0B-2B7D2C1A9F41}
AppName=Hoplet
AppVersion={#AppVersion}
AppVerName=Hoplet {#AppVersion}
AppPublisher=Hoplet
AppPublisherURL=https://github.com/saraswati-niroula/hoplet
AppSupportURL=https://github.com/saraswati-niroula/hoplet/issues
DefaultDirName={localappdata}\Programs\Hoplet
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=Hoplet-Setup
SetupIconFile=..\..\dist\hoplet.ico
UninstallDisplayIcon={app}\Hoplet.exe
UninstallDisplayName=Hoplet
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Hoplet"; Filename: "{app}\Hoplet.exe"
Name: "{autodesktop}\Hoplet"; Filename: "{app}\Hoplet.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Add a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\Hoplet.exe"; Parameters: "--show-now"; Description: "Start Hoplet now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop Hoplet, then remove its login entry and cache (settings are kept).
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im Hoplet.exe"; Flags: runhidden; RunOnceId: "StopHoplet"
Filename: "{app}\Hoplet.exe"; Parameters: "--uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "CleanupHoplet"
