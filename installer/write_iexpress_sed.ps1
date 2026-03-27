param(
    [Parameter(Mandatory = $true)]
    [string]$StageDir,
    [Parameter(Mandatory = $true)]
    [string]$OutExe,
    [Parameter(Mandatory = $true)]
    [string]$SedFile
)

$stagePath = (Resolve-Path $StageDir).Path
$files = Get-ChildItem (Join-Path $stagePath "app") -Recurse -File | Sort-Object FullName

$lines = @(
    "[Version]",
    "Class=IEXPRESS",
    "SEDVersion=3",
    "[Options]",
    "PackagePurpose=InstallApp",
    "ShowInstallProgramWindow=1",
    "HideExtractAnimation=1",
    "UseLongFileName=1",
    "InsideCompressed=0",
    "CAB_FixedSize=0",
    "CAB_ResvCodeSigning=0",
    "RebootMode=N",
    "InstallPrompt=",
    "DisplayLicense=",
    "FinishMessage=Dictly has been installed.",
    "TargetName=$OutExe",
    "FriendlyName=Dictly Setup",
    "AppLaunched=install.cmd",
    "PostInstallCmd=<None>",
    "AdminQuietInstCmd=",
    "UserQuietInstCmd=",
    "SourceFiles=SourceFiles",
    "[SourceFiles]",
    "SourceFiles0=$stagePath",
    "[SourceFiles0]",
    "%FILE0%=install.cmd"
)

$index = 1
foreach ($file in $files) {
    $relative = $file.FullName.Substring($stagePath.Length + 1)
    $lines += "%FILE$index%=$relative"
    $index += 1
}

Set-Content -Path $SedFile -Value $lines -Encoding ASCII
