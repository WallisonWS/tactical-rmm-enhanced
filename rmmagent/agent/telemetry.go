package agent

import (
	"encoding/json"
	"math"
	"runtime"
	"strings"
	"time"

	ps "github.com/elastic/go-sysinfo"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	gnet "github.com/shirou/gopsutil/v4/net"
)

type LiveTelemetrySnapshot struct {
	AgentID        string            `json:"agent_id"`
	Hostname       string            `json:"hostname"`
	Platform       string            `json:"platform"`
	Architecture   string            `json:"architecture"`
	CPULoadPercent int               `json:"cpu_load_percent"`
	CPUPerCore     []float64         `json:"cpu_per_core"`
	CPUCoresLogical int              `json:"cpu_cores_logical"`
	RAMTotalMB     uint64            `json:"ram_total_mb"`
	RAMUsedMB      uint64            `json:"ram_used_mb"`
	RAMFreeMB      uint64            `json:"ram_free_mb"`
	RAMUsedPercent int               `json:"ram_used_percent"`
	DiskMetrics    []DiskTelemetry   `json:"disk_metrics"`
	NetBytesSent   uint64            `json:"net_bytes_sent"`
	NetBytesRecv   uint64            `json:"net_bytes_recv"`
	NetPacketsSent uint64            `json:"net_packets_sent"`
	NetPacketsRecv uint64            `json:"net_packets_recv"`
	SmartHealth    []SmartDiskStatus `json:"smart_health"`
	UptimeSeconds  uint64            `json:"uptime_seconds"`
	NeedsReboot    bool              `json:"needs_reboot"`
	ProcessCount   int               `json:"process_count"`
	Timestamp      string            `json:"timestamp"`
}

type DiskTelemetry struct {
	Mountpoint  string  `json:"mountpoint"`
	Fstype      string  `json:"fstype"`
	TotalGB     float64 `json:"total_gb"`
	UsedGB      float64 `json:"used_gb"`
	FreeGB      float64 `json:"free_gb"`
	UsedPercent float64 `json:"used_percent"`
}

type SmartDiskStatus struct {
	Model        string `json:"model"`
	SerialNumber string `json:"serial_number"`
	Status       string `json:"status"`
	MediaType    string `json:"media_type"`
}

// GetLiveTelemetrySnapshot collects real-time CPU per-core load, memory usage, disk utilization, S.M.A.R.T. health, and network I/O counters.
func (a *Agent) GetLiveTelemetrySnapshot() LiveTelemetrySnapshot {
	snap := LiveTelemetrySnapshot{
		AgentID:         a.AgentID,
		Hostname:        a.Hostname,
		Platform:        runtime.GOOS,
		Architecture:    runtime.GOARCH,
		CPULoadPercent:  a.GetCPULoadAvg(),
		CPUCoresLogical: runtime.NumCPU(),
		SmartHealth:     a.GetSmartDiskHealth(),
		Timestamp:       time.Now().UTC().Format(time.RFC3339),
	}

	if perCore, err := cpu.Percent(300*time.Millisecond, true); err == nil {
		for _, v := range perCore {
			snap.CPUPerCore = append(snap.CPUPerCore, math.Round(v*10)/10)
		}
	}

	if host, err := ps.Host(); err == nil {
		if mem, mErr := host.Memory(); mErr == nil && mem.Total > 0 {
			snap.RAMTotalMB = mem.Total / (1024 * 1024)
			snap.RAMUsedMB = mem.Used / (1024 * 1024)
			if mem.Total >= mem.Used {
				snap.RAMFreeMB = (mem.Total - mem.Used) / (1024 * 1024)
			}
			snap.RAMUsedPercent = int(math.Round((float64(mem.Used) / float64(mem.Total)) * 100))
		}
	}

	if parts, err := disk.Partitions(false); err == nil {
		for _, p := range parts {
			if usage, uErr := disk.Usage(p.Mountpoint); uErr == nil && usage.Total > 0 {
				snap.DiskMetrics = append(snap.DiskMetrics, DiskTelemetry{
					Mountpoint:  p.Mountpoint,
					Fstype:      p.Fstype,
					TotalGB:     math.Round((float64(usage.Total)/(1024*1024*1024))*10) / 10,
					UsedGB:      math.Round((float64(usage.Used)/(1024*1024*1024))*10) / 10,
					FreeGB:      math.Round((float64(usage.Free)/(1024*1024*1024))*10) / 10,
					UsedPercent: math.Round(usage.UsedPercent*10) / 10,
				})
			}
		}
	}

	if ioCounters, err := gnet.IOCounters(false); err == nil && len(ioCounters) > 0 {
		snap.NetBytesSent = ioCounters[0].BytesSent
		snap.NetBytesRecv = ioCounters[0].BytesRecv
		snap.NetPacketsSent = ioCounters[0].PacketsSent
		snap.NetPacketsRecv = ioCounters[0].PacketsRecv
	}

	rebootReq, _ := a.SystemRebootRequired()
	snap.NeedsReboot = rebootReq
	snap.ProcessCount = len(a.GetProcsRPC())
	bt := a.BootTime()
	if bt > 0 && uint64(time.Now().Unix()) > bt {
		snap.UptimeSeconds = uint64(time.Now().Unix()) - bt
	}

	return snap
}

// GetSmartDiskHealth queries physical disk S.M.A.R.T. health status.
func (a *Agent) GetSmartDiskHealth() []SmartDiskStatus {
	disks := make([]SmartDiskStatus, 0)
	if runtime.GOOS == "windows" {
		psCmd := `Get-PhysicalDisk | Select-Object FriendlyName, SerialNumber, HealthStatus, MediaType | ConvertTo-Json -Compress`
		out, err := CMD("powershell.exe", []string{"-NoProfile", "-NonInteractive", "-Command", psCmd}, 15, false)
		if err == nil && strings.TrimSpace(out[0]) != "" {
			raw := strings.TrimSpace(out[0])
			if strings.HasPrefix(raw, "{") {
				var item map[string]interface{}
				if json.Unmarshal([]byte(raw), &item) == nil {
					disks = append(disks, SmartDiskStatus{
						Model:        asString(item["FriendlyName"]),
						SerialNumber: asString(item["SerialNumber"]),
						Status:       asString(item["HealthStatus"]),
						MediaType:    asString(item["MediaType"]),
					})
				}
			} else {
				var list []map[string]interface{}
				if json.Unmarshal([]byte(raw), &list) == nil {
					for _, item := range list {
						disks = append(disks, SmartDiskStatus{
							Model:        asString(item["FriendlyName"]),
							SerialNumber: asString(item["SerialNumber"]),
							Status:       asString(item["HealthStatus"]),
							MediaType:    asString(item["MediaType"]),
						})
					}
				}
			}
		}
	}
	return disks
}

func asString(v interface{}) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return strings.TrimSpace(s)
	}
	return ""
}
