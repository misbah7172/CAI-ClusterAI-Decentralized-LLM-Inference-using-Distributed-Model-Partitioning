param(
    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,

    [string]$Token,
    [string]$TokenFile,
    [string]$Distro = 'Ubuntu-22.04',
    [string]$RepoUrl = 'https://github.com/misbah7172/GreenCluster-AI-KAI.git',
    [string]$Workspace = '/opt/kai'
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir 'common.ps1')

$adminArgs = @('-ServerUrl', $ServerUrl, '-Distro', $Distro, '-RepoUrl', $RepoUrl, '-Workspace', $Workspace)
if (-not [string]::IsNullOrWhiteSpace($Token)) {
    $adminArgs += @('-Token', $Token)
}
if (-not [string]::IsNullOrWhiteSpace($TokenFile)) {
    $adminArgs += @('-TokenFile', $TokenFile)
}

Ensure-KaiAdministrator -ScriptPath $PSCommandPath -RemainingArgs $adminArgs
Ensure-KaiWslAndDistro -Distro $Distro

if ([string]::IsNullOrWhiteSpace($Token) -and -not [string]::IsNullOrWhiteSpace($TokenFile)) {
    $Token = Get-Content -LiteralPath $TokenFile -Raw
}

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw 'Provide either -Token or -TokenFile.'
}

$pythonScript = Convert-KaiWindowsPathToWsl -Path (Join-Path $scriptDir '..\bootstrap\setup_worker.py')
Invoke-KaiWslPython -PythonScriptWslPath $pythonScript -Arguments @(
    '--server-url', $ServerUrl,
    '--token', ($Token.Trim()),
    '--workspace', $Workspace,
    '--repo-url', $RepoUrl
) -Distro $Distro

Write-Host ''
Write-Host 'KAI worker node joined successfully.'
Write-Host "Connected to: $ServerUrl"
