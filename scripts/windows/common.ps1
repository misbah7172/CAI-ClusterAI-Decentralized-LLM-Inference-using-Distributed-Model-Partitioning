Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-CaiAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-CaiAdministrator {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$RemainingArgs = @()
    )

    if (Test-CaiAdministrator) {
        return
    }

    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $RemainingArgs
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList | Out-Null
    exit
}

function Test-CaiWslAvailable {
    return [bool](Get-Command wsl.exe -ErrorAction SilentlyContinue)
}

function Convert-CaiWindowsPathToWsl {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if ($resolved -match '^(?<drive>[A-Za-z]):\\(?<rest>.*)$') {
        $drive = $Matches.drive.ToLowerInvariant()
        $rest = $Matches.rest -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }

    return $resolved -replace '\\', '/'
}

function Ensure-CaiWslAndDistro {
    param(
        [string]$Distro = 'Ubuntu-22.04'
    )

    if (-not (Test-CaiWslAvailable)) {
        Write-Host 'WSL is not installed. Enabling Windows features and installing Ubuntu-22.04...'
        & dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Host
        & dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Host
        try {
            & wsl.exe --set-default-version 2 | Out-Host
        } catch {
            Write-Host 'Unable to set WSL default version right now. This is usually resolved after reboot.'
        }
        try {
            & wsl.exe --install -d $Distro --no-launch | Out-Host
        } catch {
            Write-Host 'WSL install requested a reboot or could not complete in this session.'
        }
        throw 'WSL installation has been started. Reboot Windows, then rerun this script.'
    }

    $distroList = & wsl.exe -l -q 2>$null
    if ($LASTEXITCODE -ne 0 -or ($distroList -notcontains $Distro)) {
        Write-Host "Installing WSL distro: $Distro"
        try {
            & wsl.exe --install -d $Distro --no-launch | Out-Host
        } catch {
            throw 'WSL distro installation is pending or failed. Reboot Windows, then rerun this script.'
        }

        $distroList = & wsl.exe -l -q 2>$null
        if ($distroList -notcontains $Distro) {
            throw 'WSL distro installation is still pending. Reboot Windows, then rerun this script.'
        }
    }
}

function Invoke-CaiWslPython {
    param(
        [Parameter(Mandatory = $true)][string]$PythonScriptWslPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$Distro = 'Ubuntu-22.04'
    )

    $escapedArgs = ($Arguments | ForEach-Object {
        if ($_ -match '\s') { "'$_'" } else { $_ }
    }) -join ' '
    $command = "python3 $PythonScriptWslPath $escapedArgs"
    & wsl.exe -d $Distro -- bash -lc $command
    if ($LASTEXITCODE -ne 0) {
        throw "WSL bootstrap command failed with exit code $LASTEXITCODE"
    }
}

function Get-CaiWslToken {
    param(
        [string]$TokenPath = '~/.CAI/k3s-node-token.txt',
        [string]$Distro = 'Ubuntu-22.04'
    )

    $command = "cat $TokenPath"
    $token = & wsl.exe -d $Distro -- bash -lc $command
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($token)) {
        throw 'Unable to read the K3s token from the WSL node.'
    }
    return ($token | Out-String).Trim()
}
