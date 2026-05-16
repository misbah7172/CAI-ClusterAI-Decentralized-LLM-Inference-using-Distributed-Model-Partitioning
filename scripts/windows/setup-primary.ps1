param(
    [Parameter(Mandatory = $true)]
    [string]$ServerIp,

    [string]$Distro = 'Ubuntu-22.04',
    [string]$TokenPath = '~/.kai/k3s-node-token.txt',
    [string]$RepoUrl = 'https://github.com/misbah7172/GreenCluster-AI-KAI.git',
    [string]$Workspace = '/opt/kai'
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir 'common.ps1')

Ensure-KaiAdministrator -ScriptPath $PSCommandPath -RemainingArgs @('-ServerIp', $ServerIp, '-Distro', $Distro, '-TokenPath', $TokenPath, '-RepoUrl', $RepoUrl, '-Workspace', $Workspace)
Ensure-KaiWslAndDistro -Distro $Distro

$pythonScript = Convert-KaiWindowsPathToWsl -Path (Join-Path $scriptDir '..\bootstrap\setup_primary.py')
Invoke-KaiWslPython -PythonScriptWslPath $pythonScript -Arguments @(
    '--server-ip', $ServerIp,
    '--workspace', $Workspace,
    '--repo-url', $RepoUrl,
    '--token-file', $TokenPath
) -Distro $Distro

$token = Get-KaiWslToken -TokenPath $TokenPath -Distro $Distro
$windowsTokenOut = Join-Path $scriptDir '..\..\logs\k3s-node-token.txt'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $windowsTokenOut) | Out-Null
Set-Content -Path $windowsTokenOut -Value $token -Encoding UTF8

Write-Host ''
Write-Host 'KAI primary node is ready.'
Write-Host "K3S_URL=https://${ServerIp}:6443"
Write-Host "K3S_TOKEN=$token"
Write-Host "Token copied to: $windowsTokenOut"
