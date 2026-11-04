package agent

import (
	"encoding/json"
	"fmt"
	"runtime"
	"strings"
	"time"
)

type SecurityAuditReport struct {
	AgentID             string              `json:"agent_id"`
	Hostname            string              `json:"hostname"`
	Platform            string              `json:"platform"`
	SecurityScore       int                 `json:"security_score"`
	AntivirusEnabled    bool                `json:"antivirus_enabled"`
	AntivirusName       string              `json:"antivirus_name"`
	RealtimeProtection  bool                `json:"realtime_protection"`
	FirewallEnabled     bool                `json:"firewall_enabled"`
	FirewallProfiles    []FirewallProfile   `json:"firewall_profiles"`
	DiskEncrypted       bool                `json:"disk_encrypted"`
	EncryptionDetail    string              `json:"encryption_detail"`
	UACEnabled          bool                `json:"uac_enabled"`
	RDPEnabled          bool                `json:"rdp_enabled"`
	SMBv1Enabled        bool                `json:"smbv1_enabled"`
	SuspiciousProcesses []SuspiciousProcRec `json:"suspicious_processes"`
	HighRiskOpenPorts   []int               `json:"high_risk_open_ports"`
	LocalAdmins         []string            `json:"local_admins"`
	StartupItemsCount   int                 `json:"startup_items_count"`
	Recommendations     []string            `json:"recommendations"`
	Timestamp           string              `json:"timestamp"`
}

type FirewallProfile struct {
	Name    string `json:"name"`
	Enabled bool   `json:"enabled"`
}

type SuspiciousProcRec struct {
	PID     int32  `json:"pid"`
	Name    string `json:"name"`
	Reason  string `json:"reason"`
	MemMB   uint64 `json:"mem_mb"`
	CPUPct  string `json:"cpu_pct"`
}

type StartupItem struct {
	Name     string `json:"name"`
	Command  string `json:"command"`
	Location string `json:"location"`
	User     string `json:"user"`
}

type LocalUserInfo struct {
	Username       string `json:"username"`
	Enabled        bool   `json:"enabled"`
	IsAdmin        bool   `json:"is_admin"`
	LastLogon      string `json:"last_logon"`
	PasswordExpire string `json:"password_expires"`
}

// RunSecurityAudit executes a comprehensive endpoint security & EDR posture inspection.
func (a *Agent) RunSecurityAudit() SecurityAuditReport {
	report := SecurityAuditReport{
		AgentID:          a.AgentID,
		Hostname:         a.Hostname,
		Platform:         runtime.GOOS,
		SecurityScore:    100,
		FirewallProfiles: a.GetFirewallStatus(),
		Timestamp:        time.Now().UTC().Format(time.RFC3339),
	}

	// Check Firewall status
	fwAllEnabled := len(report.FirewallProfiles) > 0
	for _, fp := range report.FirewallProfiles {
		if !fp.Enabled {
			fwAllEnabled = false
		}
	}
	report.FirewallEnabled = fwAllEnabled
	if !report.FirewallEnabled {
		report.SecurityScore -= 20
		report.Recommendations = append(report.Recommendations, "Enable all host firewall profiles (Domain, Private, Public).")
	}

	// Platform-specific security checks
	if runtime.GOOS == "windows" {
		psScript := `$ErrorActionPreference = 'SilentlyContinue'
$mp = Get-MpComputerStatus
$uac = (Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System).EnableLUA -eq 1
$rdp = (Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server').fDenyTSConnections -eq 0
$smb1 = (Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol).State -eq 'Enabled'
$bl = Get-BitLockerVolume -MountPoint $env:SystemDrive
$admins = (Get-LocalGroupMember -Group 'Administrators' | Select-Object -ExpandProperty Name)
@{
  av_enabled = [bool]$mp.AntivirusEnabled
  rtp_enabled = [bool]$mp.RealTimeProtectionEnabled
  uac_enabled = [bool]$uac
  rdp_enabled = [bool]$rdp
  smb1_enabled = [bool]$smb1
  bitlocker_status = [string]$bl.ProtectionStatus
  admins = @($admins)
} | ConvertTo-Json -Compress`

		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psScript}, 25, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			var parsed map[string]interface{}
			if json.Unmarshal([]byte(strings.TrimSpace(out[0])), &parsed) == nil {
				report.AntivirusEnabled, _ = parsed["av_enabled"].(bool)
				report.RealtimeProtection, _ = parsed["rtp_enabled"].(bool)
				if report.AntivirusEnabled {
					report.AntivirusName = "Microsoft Defender Antivirus"
				}
				report.UACEnabled, _ = parsed["uac_enabled"].(bool)
				report.RDPEnabled, _ = parsed["rdp_enabled"].(bool)
				report.SMBv1Enabled, _ = parsed["smb1_enabled"].(bool)
				blStatus, _ := parsed["bitlocker_status"].(string)
				report.DiskEncrypted = blStatus == "On" || blStatus == "1"
				report.EncryptionDetail = fmt.Sprintf("BitLocker (%s)", blStatus)
				if admList, ok := parsed["admins"].([]interface{}); ok {
					for _, adm := range admList {
						report.LocalAdmins = append(report.LocalAdmins, fmt.Sprintf("%v", adm))
					}
				}
			}
		}
	} else {
		// Linux / macOS checks
		report.AntivirusEnabled = true
		report.RealtimeProtection = true
		report.AntivirusName = "Linux Kernel Security / LSM"
		report.UACEnabled = true
		encStatus := a.GetEncryptionStatus()
		report.DiskEncrypted, _ = encStatus["encrypted"].(bool)
		report.EncryptionDetail, _ = encStatus["detail"].(string)
	}

	if !report.AntivirusEnabled || !report.RealtimeProtection {
		report.SecurityScore -= 25
		report.Recommendations = append(report.Recommendations, "Enable Antivirus and Real-Time Endpoint Protection immediately.")
	}
	if !report.DiskEncrypted {
		report.SecurityScore -= 15
		report.Recommendations = append(report.Recommendations, "Enable full-disk encryption (BitLocker / LUKS / FileVault) on system drive.")
	}
	if !report.UACEnabled {
		report.SecurityScore -= 15
		report.Recommendations = append(report.Recommendations, "Enable User Account Control (UAC) to prevent silent privilege escalation.")
	}
	if report.SMBv1Enabled {
		report.SecurityScore -= 15
		report.Recommendations = append(report.Recommendations, "Disable legacy SMBv1 protocol to mitigate lateral movement exploits.")
	}

	// Inspect processes for anomalies
	for _, p := range a.GetProcsRPC() {
		lowerName := strings.ToLower(p.Name)
		if strings.Contains(lowerName, "mimikatz") || strings.Contains(lowerName, "xmrig") || strings.Contains(lowerName, "ncat") {
			report.SuspiciousProcesses = append(report.SuspiciousProcesses, SuspiciousProcRec{
				PID:    p.PID,
				Name:   p.Name,
				Reason: "Known offensive/mining binary signature",
				MemMB:  p.Memory / (1024 * 1024),
				CPUPct: p.CPU,
			})
			report.SecurityScore -= 25
		}
	}

	// Check high-risk listening ports
	highRiskMap := map[int]bool{21: true, 23: true, 135: true, 445: true, 3389: true, 5900: true}
	seenRiskPorts := make(map[int]bool)
	for _, conn := range a.GetActiveConnections() {
		if (conn.State == "LISTENING" || conn.State == "LISTEN") && highRiskMap[conn.LocalPort] && !seenRiskPorts[conn.LocalPort] {
			seenRiskPorts[conn.LocalPort] = true
			report.HighRiskOpenPorts = append(report.HighRiskOpenPorts, conn.LocalPort)
		}
	}
	if len(report.HighRiskOpenPorts) > 2 {
		report.SecurityScore -= 10
		report.Recommendations = append(report.Recommendations, fmt.Sprintf("Restrict exposed listening ports (%v) via host firewall.", report.HighRiskOpenPorts))
	}

	startups := a.GetStartupItems()
	report.StartupItemsCount = len(startups)

	if report.SecurityScore < 0 {
		report.SecurityScore = 0
	}
	if len(report.Recommendations) == 0 {
		report.Recommendations = append(report.Recommendations, "Endpoint meets all baseline security posture checks.")
	}

	return report
}

// GetFirewallStatus returns the status of each host firewall profile.
func (a *Agent) GetFirewallStatus() []FirewallProfile {
	profiles := make([]FirewallProfile, 0)
	if runtime.GOOS == "windows" {
		psCmd := `Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json -Compress`
		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 15, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			var parsed []map[string]interface{}
			if json.Unmarshal([]byte(strings.TrimSpace(out[0])), &parsed) == nil {
				for _, item := range parsed {
					name, _ := item["Name"].(string)
					enabled := false
					switch v := item["Enabled"].(type) {
					case bool:
						enabled = v
					case float64:
						enabled = v != 0
					}
					profiles = append(profiles, FirewallProfile{Name: name, Enabled: enabled})
				}
				return profiles
			}
		}
	} else {
		// Check Fedora/RHEL firewalld first, then Ubuntu/Debian UFW
		fwOut, fwErr := CMD("firewall-cmd", []string{"--state"}, 10, false)
		if fwErr == nil && strings.Contains(strings.ToLower(fwOut[0]), "running") {
			profiles = append(profiles, FirewallProfile{Name: "Firewalld (Fedora/RHEL)", Enabled: true})
		} else {
			out, err := CMD("ufw", []string{"status"}, 10, false)
			if err == nil && strings.TrimSpace(out[0]) != "" {
				enabled := strings.Contains(strings.ToLower(out[0]), "active")
				profiles = append(profiles, FirewallProfile{Name: "UFW (Ubuntu/Debian)", Enabled: enabled})
			} else {
				profiles = append(profiles, FirewallProfile{Name: "Linux Host Firewall (UFW/Firewalld)", Enabled: false})
			}
		}
	}
	return profiles
}

// ManageFirewallRule adds, deletes, or toggles a firewall rule or profile on the endpoint (Windows Defender Firewall, Ubuntu/Debian UFW, Fedora/RHEL Firewalld).
func (a *Agent) ManageFirewallRule(action, ruleName, direction, protocol, port, remoteIP string) (map[string]interface{}, error) {
	action = strings.ToLower(strings.TrimSpace(action))
	if runtime.GOOS == "windows" {
		switch action {
		case "enable_all":
			_, err := CMD("netsh.exe", []string{"advfirewall", "set", "allprofiles", "state", "on"}, 15, false)
			return map[string]interface{}{"status": "ok", "action": action}, err
		case "disable_all":
			_, err := CMD("netsh.exe", []string{"advfirewall", "set", "allprofiles", "state", "off"}, 15, false)
			return map[string]interface{}{"status": "ok", "action": action}, err
		case "block_port":
			if ruleName == "" {
				ruleName = fmt.Sprintf("TacticalRMM_Block_%s_%s", protocol, port)
			}
			if direction == "" {
				direction = "in"
			}
			if protocol == "" {
				protocol = "TCP"
			}
			args := []string{"advfirewall", "firewall", "add", "rule", "name=" + ruleName, "dir=" + direction, "action=block", "protocol=" + protocol, "localport=" + port}
			_, err := CMD("netsh.exe", args, 15, false)
			return map[string]interface{}{"status": "ok", "rule": ruleName}, err
		case "allow_port":
			if ruleName == "" {
				ruleName = fmt.Sprintf("TacticalRMM_Allow_%s_%s", protocol, port)
			}
			if direction == "" {
				direction = "in"
			}
			if protocol == "" {
				protocol = "TCP"
			}
			args := []string{"advfirewall", "firewall", "add", "rule", "name=" + ruleName, "dir=" + direction, "action=allow", "protocol=" + protocol, "localport=" + port}
			_, err := CMD("netsh.exe", args, 15, false)
			return map[string]interface{}{"status": "ok", "rule": ruleName}, err
		case "delete_rule":
			if ruleName == "" {
				return nil, fmt.Errorf("missing rule_name")
			}
			args := []string{"advfirewall", "firewall", "delete", "rule", "name=" + ruleName}
			_, err := CMD("netsh.exe", args, 15, false)
			return map[string]interface{}{"status": "ok", "deleted": ruleName}, err
		default:
			return nil, fmt.Errorf("unsupported firewall action: %s", action)
		}
	}

	// Linux Firewall Management: Fedora/RHEL (firewall-cmd) or Ubuntu/Debian (ufw)
	proto := strings.ToLower(strings.TrimSpace(protocol))
	if proto == "" {
		proto = "tcp"
	}
	fwState, fwErr := CMD("firewall-cmd", []string{"--state"}, 5, false)
	if fwErr == nil || strings.Contains(strings.ToLower(fwState[0]), "running") {
		switch action {
		case "enable_all":
			_, err := CMD("systemctl", []string{"enable", "--now", "firewalld"}, 15, false)
			return map[string]interface{}{"status": "ok", "engine": "firewalld", "action": action}, err
		case "disable_all":
			_, err := CMD("systemctl", []string{"stop", "firewalld"}, 15, false)
			return map[string]interface{}{"status": "ok", "engine": "firewalld", "action": action}, err
		case "allow_port":
			_, err := CMD("firewall-cmd", []string{"--permanent", fmt.Sprintf("--add-port=%s/%s", port, proto)}, 15, false)
			_, _ = CMD("firewall-cmd", []string{"--reload"}, 10, false)
			return map[string]interface{}{"status": "ok", "engine": "firewalld", "allowed": fmt.Sprintf("%s/%s", port, proto)}, err
		case "block_port", "delete_rule":
			_, err := CMD("firewall-cmd", []string{"--permanent", fmt.Sprintf("--remove-port=%s/%s", port, proto)}, 15, false)
			_, _ = CMD("firewall-cmd", []string{"--reload"}, 10, false)
			return map[string]interface{}{"status": "ok", "engine": "firewalld", "blocked": fmt.Sprintf("%s/%s", port, proto)}, err
		}
	}

	// Ubuntu / Debian UFW fallback
	switch action {
	case "enable_all":
		_, err := CMD("ufw", []string{"--force", "enable"}, 15, false)
		return map[string]interface{}{"status": "ok", "engine": "ufw", "action": action}, err
	case "disable_all":
		_, err := CMD("ufw", []string{"disable"}, 15, false)
		return map[string]interface{}{"status": "ok", "engine": "ufw", "action": action}, err
	case "allow_port":
		_, err := CMD("ufw", []string{"allow", fmt.Sprintf("%s/%s", port, proto)}, 15, false)
		return map[string]interface{}{"status": "ok", "engine": "ufw", "allowed": fmt.Sprintf("%s/%s", port, proto)}, err
	case "block_port":
		_, err := CMD("ufw", []string{"deny", fmt.Sprintf("%s/%s", port, proto)}, 15, false)
		return map[string]interface{}{"status": "ok", "engine": "ufw", "blocked": fmt.Sprintf("%s/%s", port, proto)}, err
	}

	return map[string]interface{}{"status": "ok", "action": action, "platform": runtime.GOOS}, nil
}

// GetStartupItems inspects autorun persistence entries on the endpoint.
func (a *Agent) GetStartupItems() []StartupItem {
	items := make([]StartupItem, 0)
	if runtime.GOOS == "windows" {
		psCmd := `Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User | ConvertTo-Json -Compress`
		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 20, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			raw := strings.TrimSpace(out[0])
			if strings.HasPrefix(raw, "{") {
				var single StartupItem
				if json.Unmarshal([]byte(raw), &single) == nil {
					items = append(items, single)
				}
			} else {
				_ = json.Unmarshal([]byte(raw), &items)
			}
		}
	}
	return items
}

// GetLocalUsers lists local user accounts and their administrative privileges.
func (a *Agent) GetLocalUsers() []LocalUserInfo {
	users := make([]LocalUserInfo, 0)
	if runtime.GOOS == "windows" {
		psCmd := `$admins = (Get-LocalGroupMember -Group 'Administrators' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name)
Get-LocalUser | ForEach-Object {
  $isAdmin = $false
  foreach ($a in $admins) { if ($a -like "*\$($_.Name)" -or $a -eq $_.Name) { $isAdmin = $true } }
  @{
    username = $_.Name
    enabled = [bool]$_.Enabled
    is_admin = $isAdmin
    last_logon = if ($_.LastLogon) { $_.LastLogon.ToString('o') } else { 'Never' }
    password_expires = if ($_.PasswordExpires) { $_.PasswordExpires.ToString('o') } else { 'Never' }
  }
} | ConvertTo-Json -Compress`
		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 20, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			raw := strings.TrimSpace(out[0])
			if strings.HasPrefix(raw, "{") {
				var single LocalUserInfo
				if json.Unmarshal([]byte(raw), &single) == nil {
					users = append(users, single)
				}
			} else {
				_ = json.Unmarshal([]byte(raw), &users)
			}
		}
	}
	return users
}

// GetEncryptionStatus checks BitLocker (Windows), LUKS (Linux), or FileVault (macOS) status.
func (a *Agent) GetEncryptionStatus() map[string]interface{} {
	if runtime.GOOS == "windows" {
		psCmd := `Get-BitLockerVolume -MountPoint $env:SystemDrive | Select-Object MountPoint, EncryptionMethod, VolumeStatus, ProtectionStatus, EncryptionPercentage | ConvertTo-Json -Compress`
		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 15, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			var data map[string]interface{}
			if json.Unmarshal([]byte(strings.TrimSpace(out[0])), &data) == nil {
				prot := fmt.Sprintf("%v", data["ProtectionStatus"])
				return map[string]interface{}{
					"encrypted": prot == "On" || prot == "1",
					"detail":    fmt.Sprintf("BitLocker VolumeStatus=%v Protection=%v", data["VolumeStatus"], prot),
					"raw":       data,
				}
			}
		}
		return map[string]interface{}{"encrypted": false, "detail": "BitLocker inactive or unavailable"}
	}
	return map[string]interface{}{"encrypted": false, "detail": "Unverified on non-Windows host"}
}
