# Tactical RMM Enhanced — Windows & Windows Server Agent Installer
$innosetup = 'innosetupchange'
$api = '"apichange"'
$clientid = 'clientchange'
$siteid = 'sitechange'
$agenttype = '"atypechange"'
$power = powerchange
$rdp = rdpchange
$ping = pingchange
$insecure = insecurechange
$bankingSafe = bankingchange
$auth = '"tokenchange"'
$downloadlink = 'downloadchange'
$apilink = $downloadlink.split('/')

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$targetDir = 'C:\Program Files\TacticalAgent'
$targetExe = Join-Path $targetDir 'tacticalrmm.exe'
if (-not (Test-Path $targetExe)) {
    $altExe = Join-Path $targetDir 'tacticalagent.exe'
    if (Test-Path $altExe) { $targetExe = $altExe }
}

$existingSvc = Get-Service -Name 'tacticalrmm' -ErrorAction SilentlyContinue
if (-not $existingSvc) { $existingSvc = Get-Service -Name 'tacticalagent' -ErrorAction SilentlyContinue }
$regExists = Test-Path 'HKLM:\SOFTWARE\TacticalRMM'

if ($existingSvc -and $regExists -and (Test-Path $targetExe)) {
    Write-Host ('Tactical RMM Enhanced Agent is already installed.')
    if ($existingSvc.Status -ne 'Running') {
        Start-Service -Name $existingSvc.Name -ErrorAction SilentlyContinue
    }
    if ($bankingSafe -eq 1 -and ((Get-CimInstance Win32_OperatingSystem).ProductType -eq 1)) {
        Set-Service -Name 'Mesh Agent' -StartupType Manual -ErrorAction SilentlyContinue
        Stop-Service -Name 'Mesh Agent' -Force -ErrorAction SilentlyContinue
        Stop-Process -Name 'MeshAgent*' -Force -ErrorAction SilentlyContinue
    }
    exit 0
}

$OutPath = $env:TMP
$output = $innosetup

$installArgs = @('-m', 'gpoinstall', '-api', "$api", '-client-id', "$clientid", '-site-id', "$siteid", '-agent-type', "$agenttype", '-auth', "$auth", '-silent', '-gpo')

if ($power) {
    $installArgs += "-power"
}

if ($rdp) {
    $installArgs += "-rdp"
}

if ($ping) {
    $installArgs += "-ping"
}

if ($insecure -eq 1) {
    $installArgs += "-insecure"
}

$X = 0
do {
    Write-Output "Waiting for network connectivity to RMM Server ($($apilink[2]))..."
    Start-Sleep -s 3
    $X += 1
} until(($connectresult = Test-NetConnection $apilink[2] -Port 443 -ErrorAction SilentlyContinue | Where-Object { $_.TcpTestSucceeded }) -or $X -eq 3)

if ($connectresult.TcpTestSucceeded -eq $true -or $X -ge 3) {
    Try {
        $downloadedFile = Join-Path $OutPath $output
        Invoke-WebRequest -Uri $downloadlink -OutFile $downloadedFile -UseBasicParsing

        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        Start-Process -FilePath $downloadedFile -ArgumentList ('/VERYSILENT /SUPPRESSMSGBOXES') -Wait
        Start-Sleep -s 5
        if (-not (Test-Path $targetExe)) {
            $altExe = Join-Path $targetDir 'tacticalagent.exe'
            if (Test-Path $altExe) { $targetExe = $altExe }
        }
        Start-Process -FilePath $targetExe -ArgumentList $installArgs -NoNewWindow -Wait
        if ($bankingSafe -eq 1 -and ((Get-CimInstance Win32_OperatingSystem).ProductType -eq 1)) {
            Set-Service -Name 'Mesh Agent' -StartupType Manual -ErrorAction SilentlyContinue
            Stop-Service -Name 'Mesh Agent' -Force -ErrorAction SilentlyContinue
            Stop-Process -Name 'MeshAgent*' -Force -ErrorAction SilentlyContinue
        }
        exit 0
    }
    Catch {
        $ErrorMessage = $_.Exception.Message
        Write-Error -Message "$ErrorMessage"
        exit 1
    }
    Finally {
        Remove-Item -Path "$OutPath\$output" -ErrorAction SilentlyContinue
    }
} else {
    Write-Output "Unable to connect to RMM server."
}
