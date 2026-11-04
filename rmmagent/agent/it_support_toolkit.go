package agent

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

// HardwareDomainInventory holds deep hardware, BIOS, domain/Entra ID, GPU, and battery health info.
type HardwareDomainInventory struct {
	Hostname           string                   `json:"hostname"`
	Platform           string                   `json:"platform"`
	Manufacturer       string                   `json:"manufacturer"`
	Model              string                   `json:"model"`
	SerialNumber       string                   `json:"serial_number"`
	BIOSVersion        string                   `json:"bios_version"`
	DomainOrWorkgroup  string                   `json:"domain_or_workgroup"`
	PartOfDomain       bool                     `json:"part_of_domain"`
	EntraIDJoined      bool                     `json:"entra_id_joined"`
	ActivePowerPlan    string                   `json:"active_power_plan"`
	GPUs               []string                 `json:"gpus"`
	BatteryPresent     bool                     `json:"battery_present"`
	BatteryChargePct   int                      `json:"battery_charge_pct"`
	BatteryStatus      string                   `json:"battery_status"`
	PrintersCount      int                      `json:"printers_count"`
	RestorePointsCount int                      `json:"restore_points_count"`
	ExtraDetails       map[string]interface{}   `json:"extra_details"`
	Timestamp          string                   `json:"timestamp"`
}

// PrinterInfo represents an installed local or network printer on the endpoint.
type PrinterInfo struct {
	Name          string `json:"name"`
	DriverName    string `json:"driver_name"`
	PortName      string `json:"port_name"`
	PrinterStatus string `json:"printer_status"`
	Shared        bool   `json:"shared"`
	JobCount      int    `json:"job_count"`
}

// RestorePointInfo represents a Windows System Restore checkpoint.
type RestorePointInfo struct {
	SequenceNumber int    `json:"sequence_number"`
	Description    string `json:"description"`
	CreationTime   string `json:"creation_time"`
	EventType      string `json:"event_type"`
}

// GetHardwareAndDomainInventory collects deep BIOS, Service Tag, Domain/AzureAD, GPU, and Battery info.
func (a *Agent) GetHardwareAndDomainInventory() HardwareDomainInventory {
	hostname, _ := os.Hostname()
	inv := HardwareDomainInventory{
		Hostname:     hostname,
		Platform:     runtime.GOOS,
		GPUs:         []string{},
		ExtraDetails: map[string]interface{}{},
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
	}

	if runtime.GOOS == "windows" {
		psScript := `
$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$bios = Get-CimInstance Win32_BIOS -ErrorAction SilentlyContinue
$gpus = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name)
$bat = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object -First 1
$plan = (powercfg /getactivescheme) -join " "
$printers = @(Get-Printer -ErrorAction SilentlyContinue).Count
$rp = @(Get-ComputerRestorePoint -ErrorAction SilentlyContinue).Count
$dsreg = (dsregcmd /status) -join " "
$azureJoined = $dsreg -match "AzureAdJoined\s*:\s*YES"

[PSCustomObject]@{
  Manufacturer = [string]$cs.Manufacturer
  Model = [string]$cs.Model
  Domain = [string]$cs.Domain
  PartOfDomain = [bool]$cs.PartOfDomain
  SerialNumber = [string]$bios.SerialNumber
  BIOSVersion = [string]$bios.SMBIOSBIOSVersion
  GPUs = $gpus
  BatteryPresent = ($null -ne $bat)
  BatteryChargePct = if ($null -ne $bat) { [int]$bat.EstimatedChargeRemaining } else { 0 }
  BatteryStatus = if ($null -ne $bat) { [string]$bat.Status } else { "AC Power / Desktop" }
  ActivePowerPlan = [string]$plan
  PrintersCount = [int]$printers
  RestorePointsCount = [int]$rp
  EntraIDJoined = [bool]$azureJoined
} | ConvertTo-Json -Compress
`
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psScript).CombinedOutput()
		if err == nil {
			var parsed struct {
				Manufacturer       string   `json:"Manufacturer"`
				Model              string   `json:"Model"`
				Domain             string   `json:"Domain"`
				PartOfDomain       bool     `json:"PartOfDomain"`
				SerialNumber       string   `json:"SerialNumber"`
				BIOSVersion        string   `json:"BIOSVersion"`
				GPUs               []string `json:"GPUs"`
				BatteryPresent     bool     `json:"BatteryPresent"`
				BatteryChargePct   int      `json:"BatteryChargePct"`
				BatteryStatus      string   `json:"BatteryStatus"`
				ActivePowerPlan    string   `json:"ActivePowerPlan"`
				PrintersCount      int      `json:"PrintersCount"`
				RestorePointsCount int      `json:"RestorePointsCount"`
				EntraIDJoined      bool     `json:"EntraIDJoined"`
			}
			if jsonErr := json.Unmarshal(out, &parsed); jsonErr == nil {
				inv.Manufacturer = parsed.Manufacturer
				inv.Model = parsed.Model
				inv.DomainOrWorkgroup = parsed.Domain
				inv.PartOfDomain = parsed.PartOfDomain
				inv.SerialNumber = parsed.SerialNumber
				inv.BIOSVersion = parsed.BIOSVersion
				if len(parsed.GPUs) > 0 {
					inv.GPUs = parsed.GPUs
				}
				inv.BatteryPresent = parsed.BatteryPresent
				inv.BatteryChargePct = parsed.BatteryChargePct
				inv.BatteryStatus = parsed.BatteryStatus
				inv.ActivePowerPlan = parsed.ActivePowerPlan
				inv.PrintersCount = parsed.PrintersCount
				inv.RestorePointsCount = parsed.RestorePointsCount
				inv.EntraIDJoined = parsed.EntraIDJoined
			}
		}
	} else {
		// Linux / macOS DMI & system fallback
		if vendor, err := os.ReadFile("/sys/class/dmi/id/sys_vendor"); err == nil {
			inv.Manufacturer = strings.TrimSpace(string(vendor))
		}
		if prod, err := os.ReadFile("/sys/class/dmi/id/product_name"); err == nil {
			inv.Model = strings.TrimSpace(string(prod))
		}
		if serial, err := os.ReadFile("/sys/class/dmi/id/product_serial"); err == nil {
			inv.SerialNumber = strings.TrimSpace(string(serial))
		}
		if bios, err := os.ReadFile("/sys/class/dmi/id/bios_version"); err == nil {
			inv.BIOSVersion = strings.TrimSpace(string(bios))
		}
		inv.BatteryStatus = "AC Power"
	}

	return inv
}

// ManagePowerAndGPO executes common enterprise IT administrative actions (GPO update, NTP sync, Power Plan, Print Spooler reset).
func (a *Agent) ManagePowerAndGPO(action string) map[string]interface{} {
	steps := []string{}
	success := true
	output := ""

	if runtime.GOOS == "windows" {
		switch action {
		case "gpupdate_force":
			out, err := exec.Command("gpupdate", "/force").CombinedOutput()
			output = strings.TrimSpace(string(out))
			if err != nil {
				success = false
			}
			steps = append(steps, "Políticas de Grupo (Active Directory GPO) atualizadas via gpupdate /force")

		case "high_performance_power":
			_ = exec.Command("powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c").Run()
			_ = exec.Command("powercfg", "/change", "standby-timeout-ac", "0").Run()
			_ = exec.Command("powercfg", "/change", "hibernate-timeout-ac", "0").Run()
			steps = append(steps, "Plano de Energia 'Alto Desempenho' ativado e suspensão em tomada (AC) desativada")

		case "sync_time":
			_ = exec.Command("net", "start", "w32time").Run()
			out, err := exec.Command("w32tm", "/resync", "/force").CombinedOutput()
			output = strings.TrimSpace(string(out))
			if err != nil {
				success = false
			}
			steps = append(steps, "Relógio do sistema sincronizado via NTP/Active Directory (w32tm /resync)")

		case "clear_print_spooler":
			psCmd := `
Stop-Service -Name Spooler -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:SystemRoot\System32\spool\PRINTERS\*" -Force -ErrorAction SilentlyContinue
Start-Service -Name Spooler -ErrorAction SilentlyContinue
`
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			output = strings.TrimSpace(string(out))
			if err != nil {
				success = false
			}
			steps = append(steps, "Serviço Spooler reiniciado e fila de impressão limpa com sucesso")
		}
	} else {
		switch action {
		case "sync_time":
			_ = exec.Command("timedatectl", "set-ntp", "true").Run()
			steps = append(steps, "Sincronização NTP ativada via timedatectl")
		case "clear_print_spooler":
			_ = exec.Command("cancel", "-a").Run()
			_ = exec.Command("systemctl", "restart", "cups").Run()
			steps = append(steps, "Filas CUPS limpas e serviço reiniciado")
		}
	}

	return map[string]interface{}{
		"success":   success,
		"action":    action,
		"steps":     steps,
		"output":    output,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}
}

// GetPrintersAndSpooler lists all installed printers and their queue status.
func (a *Agent) GetPrintersAndSpooler() []PrinterInfo {
	printers := []PrinterInfo{}

	if runtime.GOOS == "windows" {
		psCmd := `
@(Get-Printer -ErrorAction SilentlyContinue | ForEach-Object {
  [PSCustomObject]@{
    name = [string]$_.Name
    driver_name = [string]$_.DriverName
    port_name = [string]$_.PortName
    printer_status = [string]$_.PrinterStatus
    shared = [bool]$_.Shared
    job_count = [int]$_.JobCount
  }
}) | ConvertTo-Json -Compress
`
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
		if err == nil && len(out) > 0 {
			_ = json.Unmarshal(out, &printers)
		}
	} else {
		out, err := exec.Command("lpstat", "-p").CombinedOutput()
		if err == nil {
			for _, line := range strings.Split(string(out), "\n") {
				fields := strings.Fields(line)
				if len(fields) >= 2 && fields[0] == "printer" {
					printers = append(printers, PrinterInfo{
						Name:          fields[1],
						DriverName:    "CUPS",
						PortName:      "ipp/local",
						PrinterStatus: "Normal",
					})
				}
			}
		}
	}

	return printers
}

// ManagePrinterAction clears a specific printer queue, sets default printer, or prints a test page.
func (a *Agent) ManagePrinterAction(action string, printerName string) map[string]interface{} {
	success := true
	msg := ""

	if runtime.GOOS == "windows" && printerName != "" {
		switch action {
		case "clear_queue":
			psCmd := fmt.Sprintf("Get-PrintJob -PrinterName '%s' -ErrorAction SilentlyContinue | Remove-PrintJob -ErrorAction SilentlyContinue",
				strings.ReplaceAll(printerName, "'", "''"))
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			if err != nil {
				success = false
				msg = string(out)
			} else {
				msg = fmt.Sprintf("Fila de impressão de '%s' limpa com sucesso", printerName)
			}
		case "set_default":
			psCmd := fmt.Sprintf("(New-Object -ComObject WScript.Network).SetDefaultPrinter('%s')",
				strings.ReplaceAll(printerName, "'", "''"))
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			if err != nil {
				success = false
				msg = string(out)
			} else {
				msg = fmt.Sprintf("Impressora '%s' definida como padrão", printerName)
			}
		case "test_page":
			psCmd := fmt.Sprintf("Invoke-CimMethod -InputObject (Get-CimInstance Win32_Printer -Filter \"Name='%s'\") -MethodName PrintTestPage",
				strings.ReplaceAll(printerName, "'", "''"))
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			if err != nil {
				success = false
				msg = string(out)
			} else {
				msg = fmt.Sprintf("Página de teste enviada para '%s'", printerName)
			}
		}
	}

	return map[string]interface{}{
		"success":      success,
		"action":       action,
		"printer_name": printerName,
		"message":      msg,
		"printers":     a.GetPrintersAndSpooler(),
		"timestamp":    time.Now().UTC().Format(time.RFC3339),
	}
}

// SendITSupportMessage displays an audited IT Helpdesk notification dialog to the logged-in user.
func (a *Agent) SendITSupportMessage(title string, message string, timeoutSec int) map[string]interface{} {
	if timeoutSec <= 0 {
		timeoutSec = 60
	}
	fullText := fmt.Sprintf("[%s] %s", title, message)
	success := true
	errOut := ""

	if runtime.GOOS == "windows" {
		out, err := exec.Command("msg", "*", fmt.Sprintf("/TIME:%d", timeoutSec), fullText).CombinedOutput()
		if err != nil {
			success = false
			errOut = strings.TrimSpace(string(out))
		}
	} else {
		out, err := exec.Command("wall", fullText).CombinedOutput()
		if err != nil {
			success = false
			errOut = strings.TrimSpace(string(out))
		}
	}

	return map[string]interface{}{
		"success":   success,
		"title":     title,
		"message":   message,
		"error":     errOut,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}
}

// ManageSystemRestorePoints lists or creates Windows System Restore checkpoints before maintenance.
func (a *Agent) ManageSystemRestorePoints(action string, description string) map[string]interface{} {
	points := []RestorePointInfo{}
	success := true
	msg := ""

	if runtime.GOOS == "windows" {
		if action == "create" {
			if description == "" {
				description = "Tactical RMM Pre-Maintenance Checkpoint"
			}
			safeDesc := strings.ReplaceAll(description, "'", "''")
			psCmd := fmt.Sprintf("Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue; Checkpoint-Computer -Description '%s' -RestorePointType 'MODIFY_SETTINGS'", safeDesc)
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			if err != nil {
				success = false
				msg = strings.TrimSpace(string(out))
			} else {
				msg = fmt.Sprintf("Ponto de Restauração '%s' criado com sucesso", description)
			}
		}

		listCmd := `
@(Get-ComputerRestorePoint -ErrorAction SilentlyContinue | ForEach-Object {
  [PSCustomObject]@{
    sequence_number = [int]$_.SequenceNumber
    description = [string]$_.Description
    creation_time = [string]$_.CreationTime
    event_type = [string]$_.RestorePointType
  }
}) | ConvertTo-Json -Compress
`
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", listCmd).CombinedOutput()
		if err == nil && len(out) > 0 {
			_ = json.Unmarshal(out, &points)
		}
	}

	return map[string]interface{}{
		"success":        success,
		"action":         action,
		"message":        msg,
		"restore_points": points,
		"timestamp":      time.Now().UTC().Format(time.RFC3339),
	}
}
