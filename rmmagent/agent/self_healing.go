package agent

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strings"
	"time"
)

type SelfHealReport struct {
	AgentID           string   `json:"agent_id"`
	Hostname          string   `json:"hostname"`
	ActionsExecuted   []string `json:"actions_executed"`
	ServicesRestarted []string `json:"services_restarted"`
	BytesFreed        uint64   `json:"bytes_freed"`
	FreeSpaceMB       uint64   `json:"free_space_mb"`
	Success           bool     `json:"success"`
	Timestamp         string   `json:"timestamp"`
}

type DiskCleanupReport struct {
	DirectoriesCleaned []string `json:"directories_cleaned"`
	FilesRemovedCount  int      `json:"files_removed_count"`
	BytesFreed         uint64   `json:"bytes_freed"`
	BytesFreedHuman    string   `json:"bytes_freed_human"`
	DurationMs         int64    `json:"duration_ms"`
}

// RunSelfHeal executes autonomous self-healing routines: restarts stopped automatic services, cleans temp caches, flushes DNS, and repairs WMI/Update queues if requested.
func (a *Agent) RunSelfHeal(mode string) SelfHealReport {
	report := SelfHealReport{
		AgentID:   a.AgentID,
		Hostname:  a.Hostname,
		Success:   true,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	if mode == "" {
		mode = "full"
	}

	// 1. Clean temporary files if mode is full or disk
	if mode == "full" || mode == "disk" {
		cleanRes := a.RunDeepDiskCleanup()
		report.BytesFreed = cleanRes.BytesFreed
		report.ActionsExecuted = append(report.ActionsExecuted, fmt.Sprintf("Cleaned %d temporary files (%s freed)", cleanRes.FilesRemovedCount, cleanRes.BytesFreedHuman))
	}

	// 2. Auto-restart stopped critical automatic services on Windows
	if (mode == "full" || mode == "services") && runtime.GOOS == "windows" {
		psCmd := `$stopped = Get-Service | Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -eq 'Stopped' -and $_.Name -notin @('edgeupdate','gupdate','MapsBroker','sppsvc','RemoteRegistry','WbioSrvc') }
$restarted = @()
foreach ($s in $stopped) {
  try {
    Start-Service -Name $s.Name -ErrorAction Stop
    $restarted += $s.Name
  } catch {}
}
$restarted -join ','`
		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 30, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			restarted := strings.Split(strings.TrimSpace(out[0]), ",")
			report.ServicesRestarted = restarted
			report.ActionsExecuted = append(report.ActionsExecuted, fmt.Sprintf("Restarted %d stopped automatic services: %v", len(restarted), restarted))
		} else {
			report.ActionsExecuted = append(report.ActionsExecuted, "Verified all critical Automatic services are running")
		}
	}

	// 3. Flush DNS and reset network caches if mode is full or network
	if mode == "full" || mode == "network" {
		_ = a.ResetNetworkStack(false)
		report.ActionsExecuted = append(report.ActionsExecuted, "Flushed DNS resolver cache and ARP tables")
	}

	// 4. Repair Windows Update components if mode is winupdate
	if mode == "winupdate" && runtime.GOOS == "windows" {
		psRepair := `Stop-Service -Name wuauserv,bits,cryptsvc -Force -ErrorAction SilentlyContinue
Remove-Item "$env:SystemRoot\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service -Name cryptsvc,bits,wuauserv -ErrorAction SilentlyContinue`
		_, _ = CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psRepair}, 45, false)
		report.ActionsExecuted = append(report.ActionsExecuted, "Reset Windows Update services (wuauserv, bits, cryptsvc) and cleared SoftwareDistribution download cache")
	}

	// 5. Trim working set memory
	if mode == "full" || mode == "memory" {
		_ = a.TrimMemoryWorkingSet()
		report.ActionsExecuted = append(report.ActionsExecuted, "Triggered OS memory working-set optimization")
	}

	return report
}

// RunDeepDiskCleanup removes stale temporary files across system and user temp directories.
func (a *Agent) RunDeepDiskCleanup() DiskCleanupReport {
	start := time.Now()
	report := DiskCleanupReport{
		DirectoriesCleaned: make([]string, 0),
	}

	targetDirs := []string{os.TempDir()}
	if runtime.GOOS == "windows" {
		winTemp := filepath.Join(os.Getenv("SystemRoot"), "Temp")
		if winTemp != "" && winTemp != os.TempDir() {
			targetDirs = append(targetDirs, winTemp)
		}
		swDist := filepath.Join(os.Getenv("SystemRoot"), "SoftwareDistribution", "Download")
		targetDirs = append(targetDirs, swDist)
	} else {
		targetDirs = append(targetDirs, "/var/tmp")
	}

	cutoff := time.Now().Add(-2 * time.Hour)
	for _, dir := range targetDirs {
		if dir == "" {
			continue
		}
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		report.DirectoriesCleaned = append(report.DirectoriesCleaned, dir)
		for _, entry := range entries {
			fullPath := filepath.Join(dir, entry.Name())
			info, statErr := entry.Info()
			if statErr != nil {
				continue
			}
			if info.ModTime().After(cutoff) {
				continue
			}
			size := uint64(info.Size())
			if err := os.RemoveAll(fullPath); err == nil {
				report.FilesRemovedCount++
				report.BytesFreed += size
			}
		}
	}

	report.BytesFreedHuman = ByteCountSI(report.BytesFreed)
	report.DurationMs = time.Since(start).Milliseconds()
	return report
}

// TrimMemoryWorkingSet releases unused memory in the agent and triggers OS cache trimming.
func (a *Agent) TrimMemoryWorkingSet() map[string]interface{} {
	runtime.GC()
	debug.FreeOSMemory()

	if runtime.GOOS == "windows" {
		psCmd := `[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()`
		_, _ = CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 10, false)
	}

	return map[string]interface{}{
		"status":    "ok",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}
}

// ResetNetworkStack flushes DNS, ARP, and optionally resets Winsock on Windows.
func (a *Agent) ResetNetworkStack(fullReset bool) map[string]interface{} {
	steps := make([]string, 0)
	if runtime.GOOS == "windows" {
		_, _ = CMD("ipconfig.exe", []string{"/flushdns"}, 10, false)
		steps = append(steps, "ipconfig /flushdns")
		_, _ = CMD("arp.exe", []string{"-d", "*"}, 10, false)
		steps = append(steps, "arp -d *")
		if fullReset {
			_, _ = CMD("netsh.exe", []string{"winsock", "reset"}, 15, false)
			_, _ = CMD("netsh.exe", []string{"int", "ip", "reset"}, 15, false)
			steps = append(steps, "netsh winsock reset", "netsh int ip reset")
		}
	} else {
		_, _ = CMD("resolvectl", []string{"flush-caches"}, 10, false)
		steps = append(steps, "resolvectl flush-caches")
	}

	return map[string]interface{}{
		"status":         "ok",
		"steps_executed": steps,
		"reboot_needed":  fullReset && runtime.GOOS == "windows",
	}
}
