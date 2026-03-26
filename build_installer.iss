[Setup]
AppName=Node-Mate Autonomous Agent
AppVersion=2.0
DefaultDirName={autopf}\Node-Mate
DefaultGroupName=Node-Mate
UninstallDisplayIcon={app}\Node-Mate.exe
Compression=lzma2
SolidCompression=yes
OutputDir=user_installer
OutputBaseFilename=Node-Mate-Setup
SetupIconFile=app_icon.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Node-Mate.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Node-Mate"; Filename: "{app}\Node-Mate.exe"
Name: "{group}\{cm:UninstallProgram,Node-Mate}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Node-Mate"; Filename: "{app}\Node-Mate.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Node-Mate.exe"; Description: "{cm:LaunchProgram,Node-Mate}"; Flags: nowait postinstall skipifsilent
