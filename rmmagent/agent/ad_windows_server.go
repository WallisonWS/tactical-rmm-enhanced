package agent

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	trmm "github.com/wh1te909/trmm-shared"
)

// WindowsServerADProfile holds comprehensive telemetry for both Active Directory (AD)
// and Non-AD (Workgroup / Standalone Windows Server & Workstation) environments.
type WindowsServerADProfile struct {
	Hostname                  string            `json:"hostname"`
	Platform                  string            `json:"platform"`
	OSCaption                 string            `json:"os_caption"`
	OSVersion                 string            `json:"os_version"`
	EnvironmentMode           string            `json:"environment_mode"`
	IsWindowsServer           bool              `json:"is_windows_server"`
	IsDomainController        bool              `json:"is_domain_controller"`
	PartOfDomain              bool              `json:"part_of_domain"`
	DomainName                string            `json:"domain_name"`
	WorkgroupName             string            `json:"workgroup_name"`
	ForestName                string            `json:"forest_name"`
	DomainRoleID              int               `json:"domain_role_id"`
	DomainRoleLabel           string            `json:"domain_role_label"`
	DomainControllerName      string            `json:"domain_controller_name"`
	DomainControllerAddress   string            `json:"domain_controller_address"`
	ADSiteName                string            `json:"ad_site_name"`
	ComputerDistinguishedName string            `json:"computer_dn"`
	OrganizationalUnit        string            `json:"organizational_unit"`
	SecureChannelValid        bool              `json:"secure_channel_valid"`
	SYSVOLReachable           bool              `json:"sysvol_reachable"`
	NETLOGONReachable         bool              `json:"netlogon_reachable"`
	TimeSyncSource            string            `json:"time_sync_source"`
	DeployedViaGPO            bool              `json:"deployed_via_gpo"`
	DeploymentMode            string            `json:"deployment_mode"`
	LastGPOVerify             string            `json:"last_gpo_verify"`
	AppliedComputerGPOs       []string          `json:"applied_computer_gpos"`
	InstalledServerRoles      []string          `json:"installed_server_roles"`
	ADCriticalServices        map[string]string `json:"ad_critical_services"`
	RecommendedAgentType      string            `json:"recommended_agent_type"`
	Timestamp                 string            `json:"timestamp"`
}

// mapDomainRole translates WMI Win32_ComputerSystem.DomainRole integer into a human-readable label.
func mapDomainRole(roleID int) string {
	switch roleID {
	case 0:
		return "Standalone Workstation (Sem AD / Workgroup)"
	case 1:
		return "Domain Member Workstation (Active Directory)"
	case 2:
		return "Standalone Windows Server (Sem AD / Workgroup)"
	case 3:
		return "Domain Member Windows Server (Active Directory)"
	case 4:
		return "Backup Domain Controller (BDC)"
	case 5:
		return "Primary Domain Controller (PDC)"
	default:
		return "Workstation / Endpoint"
	}
}

// extractOUFromDN parses an LDAP Distinguished Name into its OU path.
func extractOUFromDN(dn string) string {
	dn = strings.TrimSpace(dn)
	if dn == "" {
		return ""
	}
	parts := strings.Split(dn, ",")
	ouParts := make([]string, 0)
	for _, p := range parts {
		trimmed := strings.TrimSpace(p)
		upper := strings.ToUpper(trimmed)
		if strings.HasPrefix(upper, "OU=") || strings.HasPrefix(upper, "DC=") {
			ouParts = append(ouParts, trimmed)
		}
	}
	if len(ouParts) == 0 {
		return dn
	}
	return strings.Join(ouParts, ",")
}

// GetADAndWindowsServerStatus inspects Active Directory membership OR Workgroup/Standalone status,
// Windows Server roles, NTP source, and service status natively from the Go agent.
func (a *Agent) GetADAndWindowsServerStatus() WindowsServerADProfile {
	hostname, _ := os.Hostname()
	profile := WindowsServerADProfile{
		Hostname:             hostname,
		Platform:             runtime.GOOS,
		EnvironmentMode:      "workgroup_standalone",
		DomainRoleLabel:      "Standalone Endpoint",
		WorkgroupName:        "WORKGROUP",
		AppliedComputerGPOs:  []string{},
		InstalledServerRoles: []string{},
		ADCriticalServices:   map[string]string{},
		RecommendedAgentType: "workstation",
		Timestamp:            time.Now().UTC().Format(time.RFC3339),
	}

	if runtime.GOOS != "windows" {
		profile.OSCaption = a.osString()
		profile.EnvironmentMode = "linux_standalone"
		if out, err := exec.Command("realm", "list").CombinedOutput(); err == nil && len(out) > 0 {
			text := strings.TrimSpace(string(out))
			if text != "" {
				profile.PartOfDomain = true
				profile.EnvironmentMode = "active_directory"
				for _, line := range strings.Split(text, "\n") {
					line = strings.TrimSpace(line)
					if strings.HasPrefix(line, "domain-name:") {
						profile.DomainName = strings.TrimSpace(strings.TrimPrefix(line, "domain-name:"))
					}
				}
			}
		}
		return profile
	}

	psScript := `
$ErrorActionPreference = 'SilentlyContinue'
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$prodType = [int]$os.ProductType
$domainRole = [int]$cs.DomainRole
$partOfDomain = [bool]$cs.PartOfDomain
$domainName = [string]$cs.Domain
$workgroupName = if ([string]$cs.Workgroup -ne "") { [string]$cs.Workgroup } else { $domainName }
$isServer = ($prodType -eq 2 -or $prodType -eq 3 -or $domainRole -ge 2)
$isDC = ($prodType -eq 2 -or $domainRole -ge 4)

$dcName = ""
$dcAddr = ""
$adSite = ""
$forestName = ""
$compDN = ""
$secureChan = $false
$sysvolOk = $false
$netlogonOk = $false

if ($partOfDomain -and $domainName -ne "") {
  try {
    $domObj = [System.DirectoryServices.ActiveDirectory.Domain]::GetComputerDomain()
    if ($null -ne $domObj) {
      $forestName = [string]$domObj.Forest.Name
      $pdc = $domObj.FindDomainController()
      if ($null -ne $pdc) {
        $dcName = [string]$pdc.Name
        $dcAddr = [string]$pdc.IPAddress
        $adSite = [string]$pdc.SiteName
      }
    }
  } catch {}

  try {
    $searcher = New-Object System.DirectoryServices.DirectorySearcher
    $searcher.Filter = "(&(objectCategory=computer)(cn=$env:COMPUTERNAME))"
    $res = $searcher.FindOne()
    if ($null -ne $res) {
      $compDN = [string]$res.Properties["distinguishedname"][0]
    }
  } catch {}

  try {
    if ($isDC) {
      $secureChan = $true
    } else {
      $secureChan = [bool](Test-ComputerSecureChannel -ErrorAction SilentlyContinue)
    }
  } catch {}

  $sysvolOk = Test-Path "\\$domainName\SYSVOL"
  $netlogonOk = Test-Path "\\$domainName\NETLOGON"
}

$timeSource = ""
try {
  $timeSource = [string](w32tm /query /source)
} catch {}

$gpos = @()
try {
  $gpKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Group Policy\State\Machine\GPO-List"
  if (Test-Path $gpKey) {
    $gpos = @(Get-ChildItem $gpKey | ForEach-Object {
      (Get-ItemProperty $_.PSPath).DisplayName
    } | Where-Object { $_ -ne $null -and $_ -ne "" } | Select-Object -Unique)
  }
} catch {}

$roles = @()
if ($isServer) {
  try {
    $roles = @(Get-WindowsFeature | Where-Object { $_.Installed -eq $true -and $_.FeatureType -eq 'Role' } | Select-Object -ExpandProperty Name)
  } catch {}
}

$svcNames = @('Netlogon', 'W32Time', 'LanmanWorkstation', 'LanmanServer', 'DNS', 'NTDS', 'Kdc', 'DFSR', 'tacticalrmm', 'Mesh Agent')
$svcs = @{}
foreach ($s in $svcNames) {
  $svcObj = Get-Service -Name $s -ErrorAction SilentlyContinue
  if ($null -ne $svcObj) {
    $svcs[$s] = [string]$svcObj.Status
  }
}

$trmmKey = "HKLM:\SOFTWARE\TacticalRMM"
$deployedVia = ""
$lastGpoVerify = ""
if (Test-Path $trmmKey) {
  $props = Get-ItemProperty $trmmKey -ErrorAction SilentlyContinue
  $deployedVia = [string]$props.DeployedVia
  $lastGpoVerify = [string]$props.LastGPOVerify
}

[PSCustomObject]@{
  OSCaption = [string]$os.Caption
  OSVersion = [string]$os.Version
  IsWindowsServer = [bool]$isServer
  IsDomainController = [bool]$isDC
  PartOfDomain = [bool]$partOfDomain
  DomainName = $domainName
  WorkgroupName = $workgroupName
  ForestName = $forestName
  DomainRoleID = $domainRole
  DCName = $dcName
  DCAddr = $dcAddr
  ADSite = $adSite
  ComputerDN = $compDN
  SecureChannel = [bool]$secureChan
  SysvolOk = [bool]$sysvolOk
  NetlogonOk = [bool]$netlogonOk
  TimeSource = ($timeSource -join " ").Trim()
  DeployedVia = $deployedVia
  LastGPOVerify = $lastGpoVerify
  AppliedGPOs = $gpos
  ServerRoles = $roles
  Services = $svcs
} | ConvertTo-Json -Compress -Depth 4
`
	out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psScript).CombinedOutput()
	if err == nil && len(out) > 0 {
		var parsed struct {
			OSCaption          string            `json:"OSCaption"`
			OSVersion          string            `json:"OSVersion"`
			IsWindowsServer    bool              `json:"IsWindowsServer"`
			IsDomainController bool              `json:"IsDomainController"`
			PartOfDomain       bool              `json:"PartOfDomain"`
			DomainName         string            `json:"DomainName"`
			WorkgroupName      string            `json:"WorkgroupName"`
			ForestName         string            `json:"ForestName"`
			DomainRoleID       int               `json:"DomainRoleID"`
			DCName             string            `json:"DCName"`
			DCAddr             string            `json:"DCAddr"`
			ADSite             string            `json:"ADSite"`
			ComputerDN         string            `json:"ComputerDN"`
			SecureChannel      bool              `json:"SecureChannel"`
			SysvolOk           bool              `json:"SysvolOk"`
			NetlogonOk         bool              `json:"NetlogonOk"`
			TimeSource         string            `json:"TimeSource"`
			DeployedVia        string            `json:"DeployedVia"`
			LastGPOVerify      string            `json:"LastGPOVerify"`
			AppliedGPOs        []string          `json:"AppliedGPOs"`
			ServerRoles        []string          `json:"ServerRoles"`
			Services           map[string]string `json:"Services"`
		}
		if jsonErr := json.Unmarshal(out, &parsed); jsonErr == nil {
			profile.OSCaption = parsed.OSCaption
			profile.OSVersion = parsed.OSVersion
			profile.IsWindowsServer = parsed.IsWindowsServer
			profile.IsDomainController = parsed.IsDomainController
			profile.PartOfDomain = parsed.PartOfDomain
			profile.DomainName = parsed.DomainName
			profile.WorkgroupName = parsed.WorkgroupName
			profile.ForestName = parsed.ForestName
			profile.DomainRoleID = parsed.DomainRoleID
			profile.DomainRoleLabel = mapDomainRole(parsed.DomainRoleID)
			profile.DomainControllerName = parsed.DCName
			profile.DomainControllerAddress = parsed.DCAddr
			profile.ADSiteName = parsed.ADSite
			profile.ComputerDistinguishedName = parsed.ComputerDN
			profile.OrganizationalUnit = extractOUFromDN(parsed.ComputerDN)
			profile.SecureChannelValid = parsed.SecureChannel
			profile.SYSVOLReachable = parsed.SysvolOk
			profile.NETLOGONReachable = parsed.NetlogonOk
			profile.TimeSyncSource = parsed.TimeSource
			profile.DeploymentMode = parsed.DeployedVia
			profile.DeployedViaGPO = strings.Contains(strings.ToLower(parsed.DeployedVia), "gpo")
			profile.LastGPOVerify = parsed.LastGPOVerify
			if parsed.PartOfDomain {
				profile.EnvironmentMode = "active_directory"
			} else {
				profile.EnvironmentMode = "workgroup_standalone"
			}
			if len(parsed.AppliedGPOs) > 0 {
				profile.AppliedComputerGPOs = parsed.AppliedGPOs
			}
			if len(parsed.ServerRoles) > 0 {
				profile.InstalledServerRoles = parsed.ServerRoles
			}
			if len(parsed.Services) > 0 {
				profile.ADCriticalServices = parsed.Services
			}
			if parsed.IsWindowsServer || parsed.IsDomainController || parsed.DomainRoleID >= 2 {
				profile.RecommendedAgentType = "server"
			} else {
				profile.RecommendedAgentType = "workstation"
			}
		}
	}

	return profile
}

// AutoSelectAgentType inspects the OS role in Golang and automatically returns "server" for
// Windows Server (both AD and Standalone/Workgroup) and "workstation" for client OS.
func (a *Agent) AutoSelectAgentType(requestedType string) string {
	clean := strings.ToLower(strings.TrimSpace(requestedType))
	if clean == "server" || clean == "workstation" {
		if runtime.GOOS == "windows" {
			profile := a.GetADAndWindowsServerStatus()
			if profile.IsWindowsServer || profile.IsDomainController || profile.DomainRoleID >= 2 {
				return "server"
			}
		}
		return clean
	}
	profile := a.GetADAndWindowsServerStatus()
	if profile.RecommendedAgentType == "server" {
		return "server"
	}
	return "workstation"
}

// EnsureGPOInstallAndSelfHeal provides an idempotent, zero-popup installer and health check in Golang
// that works in both Active Directory (GPO) and Non-AD (Standalone / Workgroup) units.
func (a *Agent) EnsureGPOInstallAndSelfHeal(i *Installer) map[string]interface{} {
	steps := []string{}
	i.Silent = true

	adProfile := a.GetADAndWindowsServerStatus()
	deployLabel := "Standalone-Workgroup"
	if adProfile.PartOfDomain {
		deployLabel = "ActiveDirectory-GPO"
	}

	if runtime.GOOS == "windows" {
		checkPS := `
$k = "HKLM:\SOFTWARE\TacticalRMM"
if (Test-Path $k) {
  $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
  if ($p.AgentID -and $p.Token -and $p.BaseURL) {
    Write-Output "INSTALLED:$($p.AgentID)"
  }
}
`
		out, _ := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", checkPS).CombinedOutput()
		statusStr := strings.TrimSpace(string(out))

		if strings.HasPrefix(statusStr, "INSTALLED:") {
			existingAgentID := strings.TrimPrefix(statusStr, "INSTALLED:")
			steps = append(steps, fmt.Sprintf("Agente já registrado (AgentID: %s | Modo: %s). Verificando serviços...", existingAgentID, deployLabel))

			for _, binName := range []string{"tacticalrmm.exe", "tacticalagent.exe"} {
				targetExe := filepath.Join(a.ProgramDir, binName)
				if !trmm.FileExists(targetExe) {
					if selfExe, err := os.Executable(); err == nil {
						_ = os.MkdirAll(a.ProgramDir, 0755)
						if copyErr := copyFile(selfExe, targetExe); copyErr == nil {
							steps = append(steps, fmt.Sprintf("Binário %s restaurado em C:\\Program Files\\TacticalAgent", binName))
						}
					}
				}
			}

			_ = a.InstallService()
			svcRes := a.ControlService("tacticalrmm", "start")
			if svcRes.Success {
				steps = append(steps, "Serviço Windows 'tacticalrmm' ativo")
			}

			if _, meshErr := a.getMeshNodeID(); meshErr != nil {
				steps = append(steps, "Sincronizando Mesh Agent via RecoverMesh()...")
				a.RecoverMesh()
			} else {
				_ = exec.Command("net", "start", a.MeshSVC).Run()
				a.SyncMeshNodeID(false)
				steps = append(steps, "Serviço 'Mesh Agent' e NodeID sincronizados")
			}

			stampPS := fmt.Sprintf(`
$k = "HKLM:\SOFTWARE\TacticalRMM"
if (Test-Path $k) {
  Set-ItemProperty -Path $k -Name "DeployedVia" -Value "%s" -ErrorAction SilentlyContinue
  Set-ItemProperty -Path $k -Name "LastGPOVerify" -Value "%s" -ErrorAction SilentlyContinue
}
`, deployLabel, time.Now().UTC().Format(time.RFC3339))
			_ = exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", stampPS).Run()

			a.DoNatsCheckIn()
			return map[string]interface{}{
				"status":           "already_installed_verified",
				"agent_id":         existingAgentID,
				"environment_mode": adProfile.EnvironmentMode,
				"steps":            steps,
			}
		}

		_ = os.MkdirAll(a.ProgramDir, 0755)
		if selfExe, err := os.Executable(); err == nil {
			cleanSelf := filepath.Clean(selfExe)
			for _, binName := range []string{"tacticalrmm.exe", "tacticalagent.exe"} {
				targetExe := filepath.Join(a.ProgramDir, binName)
				cleanTarget := filepath.Clean(targetExe)
				if !strings.EqualFold(cleanSelf, cleanTarget) {
					if copyErr := copyFile(cleanSelf, cleanTarget); copyErr == nil {
						steps = append(steps, fmt.Sprintf("Binário Go copiado para %s", cleanTarget))
					}
				}
			}
		}
	}

	i.AgentType = a.AutoSelectAgentType(i.AgentType)

	if strings.TrimSpace(i.Description) == "" || strings.EqualFold(strings.TrimSpace(i.Description), "auto") {
		if adProfile.PartOfDomain && adProfile.DomainName != "" {
			if adProfile.OrganizationalUnit != "" {
				i.Description = fmt.Sprintf("AD [%s | %s]", adProfile.DomainName, adProfile.OrganizationalUnit)
			} else {
				i.Description = fmt.Sprintf("AD [%s - %s]", adProfile.DomainName, adProfile.DomainRoleLabel)
			}
		} else {
			wg := adProfile.WorkgroupName
			if wg == "" {
				wg = "WORKGROUP"
			}
			i.Description = fmt.Sprintf("Unidade Sem AD [%s - %s]", wg, adProfile.DomainRoleLabel)
		}
	}

	a.Install(i)

	if runtime.GOOS == "windows" {
		stampPS := fmt.Sprintf(`
$k = "HKLM:\SOFTWARE\TacticalRMM"
if (Test-Path $k) {
  Set-ItemProperty -Path $k -Name "DeployedVia" -Value "%s" -ErrorAction SilentlyContinue
  Set-ItemProperty -Path $k -Name "LastGPOVerify" -Value "%s" -ErrorAction SilentlyContinue
}
`, deployLabel, time.Now().UTC().Format(time.RFC3339))
		_ = exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", stampPS).Run()
	}

	steps = append(steps, fmt.Sprintf("Instalação concluída (Tipo: %s | Ambiente: %s)", i.AgentType, deployLabel))
	return map[string]interface{}{
		"status":           "fresh_install_completed",
		"agent_type":       i.AgentType,
		"environment_mode": adProfile.EnvironmentMode,
		"steps":            steps,
	}
}

// ManageActiveDirectoryAndServer executes maintenance actions for both Active Directory
// and Non-AD (Workgroup / Standalone Windows Server & Workstation) endpoints in Golang.
func (a *Agent) ManageActiveDirectoryAndServer(action string) map[string]interface{} {
	steps := []string{}
	success := true
	output := ""

	if runtime.GOOS != "windows" {
		if action == "sync_standalone_ntp" {
			_ = exec.Command("timedatectl", "set-ntp", "true").Run()
			steps = append(steps, "Sincronização NTP habilitada no servidor Linux via timedatectl")
		} else {
			success = false
			output = "Ação disponível para sistemas Windows Server / Workstation"
		}
		return map[string]interface{}{
			"success":    success,
			"action":     action,
			"steps":      steps,
			"output":     output,
			"ad_profile": a.GetADAndWindowsServerStatus(),
			"timestamp":  time.Now().UTC().Format(time.RFC3339),
		}
	}

	profile := a.GetADAndWindowsServerStatus()

	switch action {
	case "test_secure_channel":
		if !profile.PartOfDomain {
			output = fmt.Sprintf("Unidade Sem AD (Workgroup: %s | Função: %s). Operando em modo Standalone.", profile.WorkgroupName, profile.DomainRoleLabel)
			steps = append(steps, "Verificado modo Standalone / Workgroup (Unidade sem Active Directory)")
		} else {
			psCmd := `
$cs = Get-CimInstance Win32_ComputerSystem
$ok = Test-ComputerSecureChannel -Verbose 4>&1
$nl = nltest /sc_query:$($cs.Domain) 2>&1
Write-Output "Test-ComputerSecureChannel: $($ok -join ' ')` + "\n" + `$($nl -join "` + "\n" + `")"
`
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			output = strings.TrimSpace(string(out))
			if err != nil {
				success = false
			}
			steps = append(steps, "Canal Seguro do Active Directory verificado via Test-ComputerSecureChannel")
		}

	case "repair_secure_channel":
		if !profile.PartOfDomain {
			_ = exec.Command("net", "start", "w32time").Run()
			out, _ := exec.Command("w32tm", "/resync", "/force").CombinedOutput()
			output = fmt.Sprintf("Unidade Sem AD (%s): Serviços locais e horário sincronizados.\n%s", profile.WorkgroupName, strings.TrimSpace(string(out)))
			steps = append(steps, "Unidade Sem AD: Serviços locais e W32Time ressincronizados")
		} else {
			psCmd := `
$rep = Test-ComputerSecureChannel -Repair -ErrorAction SilentlyContinue
Restart-Service -Name Netlogon -Force -ErrorAction SilentlyContinue
w32tm /resync /force | Out-Null
Write-Output "Canal seguro reparado: $rep | Serviço Netlogon reiniciado e W32Time sincronizado."
`
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			output = strings.TrimSpace(string(out))
			if err != nil {
				success = false
			}
			steps = append(steps, "Reparo do Canal Seguro do Active Directory (Netlogon + W32Time) executado")
		}

	case "gpupdate_registerdns":
		_ = exec.Command("ipconfig", "/flushdns").Run()
		if profile.PartOfDomain {
			_ = exec.Command("ipconfig", "/registerdns").Run()
			_ = exec.Command("klist", "purge").Run()
		}
		out, err := exec.Command("gpupdate", "/force").CombinedOutput()
		output = strings.TrimSpace(string(out))
		if err != nil {
			success = false
		}
		if profile.PartOfDomain {
			steps = append(steps, "Cache DNS limpo, DNS registrado no AD e GPOs de Domínio atualizadas")
		} else {
			steps = append(steps, "Cache DNS limpo e Políticas de Grupo Locais (LGPO) atualizadas na unidade sem AD")
		}

	case "sync_standalone_ntp":
		psCmd := `
Start-Service -Name w32time -ErrorAction SilentlyContinue
w32tm /config /manualpeerlist:"a.st1.ntp.br,b.st1.ntp.br,pool.ntp.org" /syncfromflags:manual /reliable:yes /update
w32tm /resync /force
w32tm /query /status
`
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
		output = strings.TrimSpace(string(out))
		if err != nil {
			success = false
		}
		steps = append(steps, "Sincronismo NTP Standalone (a.st1.ntp.br / pool.ntp.org) configurado e atualizado para unidade sem AD")

	case "dcdiag_server_health":
		psCmd := `
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$report = @()
$report += "OS: $($os.Caption) ($($os.Version))"
if ($cs.PartOfDomain) {
  $report += "Modo: Active Directory Domain ($($cs.Domain)) | RoleID: $($cs.DomainRole)"
  $dc = nltest /dsgetdc:$($cs.Domain) 2>&1
  $report += ($dc -join "` + "\n" + `")
} else {
  $report += "Modo: Unidade Sem AD / Workgroup ($($cs.Workgroup)) | RoleID: $($cs.DomainRole)"
}
$w32 = w32tm /query /status 2>&1
$report += "--- Status de Horário (W32Time) ---"
$report += ($w32 -join "` + "\n" + `")
$report -join "` + "\n" + `"
`
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
		output = strings.TrimSpace(string(out))
		if err != nil {
			success = false
		}
		steps = append(steps, "Diagnóstico de Windows Server / Endpoint (AD e Workgroup Standalone) concluído")
	}

	return map[string]interface{}{
		"success":    success,
		"action":     action,
		"steps":      steps,
		"output":     output,
		"ad_profile": a.GetADAndWindowsServerStatus(),
		"timestamp":  time.Now().UTC().Format(time.RFC3339),
	}
}
