# Tactical RMM Enhanced — Windows PowerShell Agent Installer
# Supports: Windows 10, Windows 11, Windows Server 2016 / 2019 / 2022 / 2025
$innosetup = 'innosetupchange'
$api = '"apichange"'
$clientid = 'clientchange'
$siteid = 'sitechange'
$agenttype = '"atypechange"'
$power = powerchange
$rdp = rdpchange
$ping = pingchange
$insecure = insecurechange
$auth = '"tokenchange"'
$downloadlink = 'downloadchange'
$apilink = $downloadlink.split('/')

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

if ($insecure -eq 1) {
    add-type @"
        using System.Net;
        using System.Security.Cryptography.X509Certificates;
        public class TrustAllCertsPolicy : ICertificatePolicy {
            public bool CheckValidationResult(
                ServicePoint srvPoint, X509Certificate certificate,
                WebRequest request, int certificateProblem) {
                return true;
            }
        }
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
}

$serviceName = 'tacticalrmm'
If (Get-Service $serviceName -ErrorAction SilentlyContinue) {
    Write-Host ('Tactical RMM Enhanced Agent is already installed.')
} Else {
    $OutPath = $env:TMP
    $output = $innosetup

    $installArgs = @('-m install --api ', "$api", '--client-id', $clientid, '--site-id', $siteid, '--agent-type', "$agenttype", '--auth', "$auth")

    if ($power) {
        $installArgs += "--power"
    }

    if ($rdp) {
        $installArgs += "--rdp"
    }

    if ($ping) {
        $installArgs += "--ping"
    }

    if ($insecure -eq 1) {
        $installArgs += "--insecure"
    }

    Try {
        $DefenderStatus = Get-MpComputerStatus -ErrorAction SilentlyContinue | Select-Object AntivirusEnabled
        if ($DefenderStatus -match "True") {
            Add-MpPreference -ExclusionPath 'C:\Program Files\TacticalAgent\*' -ErrorAction SilentlyContinue
            Add-MpPreference -ExclusionPath 'C:\Program Files\Mesh Agent\*' -ErrorAction SilentlyContinue
            Add-MpPreference -ExclusionPath 'C:\ProgramData\TacticalRMM\*' -ErrorAction SilentlyContinue
            Add-MpPreference -ExclusionProcess 'C:\Windows\Temp\is-*.tmp\tacticalagent*' -ErrorAction SilentlyContinue
        }
    }
    Catch {
        # pass
    }

    $X = 0
    do {
        Write-Output "Waiting for network connectivity to RMM Server ($($apilink[2]))..."
        Start-Sleep -s 3
        $X += 1
    } until(($connectresult = Test-NetConnection $apilink[2] -Port 443 -ErrorAction SilentlyContinue | Where-Object { $_.TcpTestSucceeded }) -or $X -eq 3)

    if ($connectresult.TcpTestSucceeded -eq $true -or $X -ge 3) {
        Try {
            Invoke-WebRequest -Uri $downloadlink -OutFile "$OutPath\$output" -UseBasicParsing
            Start-Process -FilePath "$OutPath\$output" -ArgumentList ('/VERYSILENT /SUPPRESSMSGBOXES') -Wait
            Write-Host ('Extracting and registering Tactical RMM Enhanced Agent...')
            Start-Sleep -s 6
            Start-Process -FilePath "C:\Program Files\TacticalAgent\tacticalrmm.exe" -ArgumentList $installArgs -Wait
            sc.exe failure tacticalrmm reset= 0 actions= restart/5000/restart/5000/restart/5000 | Out-Null
            exit 0
        }
        Catch {
            $ErrorMessage = $_.Exception.Message
            $FailedItem = $_.Exception.ItemName
            Write-Error -Message "$ErrorMessage $FailedItem"
            exit 1
        }
        Finally {
            Remove-Item -Path "$OutPath\$output" -ErrorAction SilentlyContinue
        }
    } else {
        Write-Output "Unable to connect to RMM server."
    }
}
