package agent

import (
	"encoding/json"
	"fmt"
	"net"
	"os/exec"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

// DiscoveredLANHost represents a computer or device found on the unit's local network via the server.
type DiscoveredLANHost struct {
	IPAddress       string   `json:"ip_address"`
	Hostname        string   `json:"hostname"`
	MACAddress      string   `json:"mac_address"`
	DiscoverySource []string `json:"discovery_source"`
	OpenServices    []string `json:"open_services"`
	EstimatedType   string   `json:"estimated_type"`
	SMBUser         string   `json:"smb_user"`
	Reachable       bool     `json:"reachable"`
}

// UnitLANDiscoveryReport holds the full computer inventory discovered from a unit's server.
type UnitLANDiscoveryReport struct {
	ServerHostname string              `json:"server_hostname"`
	ServerPlatform string              `json:"server_platform"`
	LocalSubnets   []string            `json:"local_subnets"`
	TotalFound     int                 `json:"total_found"`
	ComputersCount int                 `json:"computers_count"`
	Hosts          []DiscoveredLANHost `json:"hosts"`
	DurationMs     int64               `json:"duration_ms"`
	Timestamp      string              `json:"timestamp"`
}

// DiscoverUnitLANComputers performs an enterprise asset inventory ("Levantamento de Computadores")
// from a standalone server in units without Active Directory using:
// 1. Active SMB / File Share client sessions connected to the server
// 2. Local DHCP Server leases (if the server hosts DHCP)
// 3. Local ARP / Neighbor cache
// 4. Concurrent Golang TCP/DNS probe across the server's local /24 subnet
func (a *Agent) DiscoverUnitLANComputers(customSubnet string) UnitLANDiscoveryReport {
	start := time.Now()
	report := UnitLANDiscoveryReport{
		ServerHostname: a.Hostname,
		ServerPlatform: runtime.GOOS,
		LocalSubnets:   []string{},
		Hosts:          []DiscoveredLANHost{},
		Timestamp:      time.Now().UTC().Format(time.RFC3339),
	}

	hostMap := make(map[string]*DiscoveredLANHost)
	var mu sync.Mutex

	upsertHost := func(ip, hostname, mac, source, smbUser string) {
		ip = strings.TrimSpace(ip)
		if ip == "" || ip == "127.0.0.1" || ip == "::1" || strings.HasPrefix(ip, "169.254.") || strings.HasPrefix(ip, "224.") || strings.HasPrefix(ip, "239.") || strings.HasSuffix(ip, ".255") {
			return
		}
		parsed := net.ParseIP(ip)
		if parsed == nil || parsed.To4() == nil {
			return
		}

		mu.Lock()
		defer mu.Unlock()
		entry, exists := hostMap[ip]
		if !exists {
			entry = &DiscoveredLANHost{
				IPAddress:       ip,
				Hostname:        strings.TrimSuffix(strings.TrimSpace(hostname), "."),
				MACAddress:      strings.ToUpper(strings.TrimSpace(mac)),
				DiscoverySource: []string{},
				OpenServices:    []string{},
				EstimatedType:   "Dispositivo de Rede",
				SMBUser:         strings.TrimSpace(smbUser),
				Reachable:       true,
			}
			hostMap[ip] = entry
		} else {
			if entry.Hostname == "" && strings.TrimSpace(hostname) != "" {
				entry.Hostname = strings.TrimSuffix(strings.TrimSpace(hostname), ".")
			}
			if entry.MACAddress == "" && strings.TrimSpace(mac) != "" {
				entry.MACAddress = strings.ToUpper(strings.TrimSpace(mac))
			}
			if entry.SMBUser == "" && strings.TrimSpace(smbUser) != "" {
				entry.SMBUser = strings.TrimSpace(smbUser)
			}
		}

		if source != "" {
			hasSrc := false
			for _, s := range entry.DiscoverySource {
				if s == source {
					hasSrc = true
					break
				}
			}
			if !hasSrc {
				entry.DiscoverySource = append(entry.DiscoverySource, source)
			}
		}
	}

	// 1. Collect local IPv4 subnets on this server
	subnetPrefixes := make([]string, 0)
	localIPs := make(map[string]bool)
	if strings.TrimSpace(customSubnet) != "" {
		parts := strings.Split(strings.TrimSpace(customSubnet), ".")
		if len(parts) >= 3 {
			pref := fmt.Sprintf("%s.%s.%s", parts[0], parts[1], parts[2])
			subnetPrefixes = append(subnetPrefixes, pref)
			report.LocalSubnets = append(report.LocalSubnets, pref+".0/24")
		}
	} else {
		ifaces, err := net.Interfaces()
		if err == nil {
			for _, iface := range ifaces {
				if (iface.Flags&net.FlagUp) == 0 || (iface.Flags&net.FlagLoopback) != 0 {
					continue
				}
				addrs, err := iface.Addrs()
				if err != nil {
					continue
				}
				for _, addr := range addrs {
					var ip net.IP
					switch v := addr.(type) {
					case *net.IPNet:
						ip = v.IP
					case *net.IPAddr:
						ip = v.IP
					}
					if ip == nil || ip.IsLoopback() {
						continue
					}
					ipv4 := ip.To4()
					if ipv4 == nil {
						continue
					}
					ipStr := ipv4.String()
					if strings.HasPrefix(ipStr, "169.254.") || strings.HasPrefix(ipStr, "172.17.") {
						continue
					}
					localIPs[ipStr] = true
					octets := strings.Split(ipStr, ".")
					if len(octets) == 4 {
						pref := fmt.Sprintf("%s.%s.%s", octets[0], octets[1], octets[2])
						already := false
						for _, existing := range subnetPrefixes {
							if existing == pref {
								already = true
								break
							}
						}
						if !already && len(subnetPrefixes) < 2 {
							subnetPrefixes = append(subnetPrefixes, pref)
							report.LocalSubnets = append(report.LocalSubnets, pref+".0/24")
						}
					}
				}
			}
		}
	}

	// 2. Windows Server SMB Sessions, DHCP Leases & ARP Neighbor Table
	if runtime.GOOS == "windows" {
		psCollect := `
$ErrorActionPreference = 'SilentlyContinue'
$items = @()

try {
  Get-SmbSession | ForEach-Object {
    $cip = [string]$_.ClientComputerName
    $cip = $cip.TrimStart('\')
    $items += [PSCustomObject]@{
      IP = $cip
      Hostname = ""
      MAC = ""
      Source = "Sessão SMB (Acesso ao Servidor)"
      User = [string]$_.ClientUserName
    }
  }
} catch {}

try {
  Get-DhcpServerv4Scope | ForEach-Object {
    Get-DhcpServerv4Lease -ScopeId $_.ScopeId | ForEach-Object {
      $items += [PSCustomObject]@{
        IP = [string]$_.IPAddress
        Hostname = [string]$_.HostName
        MAC = [string]$_.ClientId
        Source = "DHCP Server Lease"
        User = ""
      }
    }
  }
} catch {}

try {
  Get-NetNeighbor -AddressFamily IPv4 | Where-Object { $_.State -in @('Reachable','Stale','Permanent','Delay','Probe') -and $_.LinkLayerAddress -ne '' -and $_.LinkLayerAddress -ne '00-00-00-00-00-00' } | ForEach-Object {
    $items += [PSCustomObject]@{
      IP = [string]$_.IPAddress
      Hostname = ""
      MAC = [string]$_.LinkLayerAddress
      Source = "Tabela ARP"
      User = ""
    }
  }
} catch {}

$items | ConvertTo-Json -Compress
`
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCollect).CombinedOutput()
		if err == nil && len(out) > 0 {
			type psItem struct {
				IP       string `json:"IP"`
				Hostname string `json:"Hostname"`
				MAC      string `json:"MAC"`
				Source   string `json:"Source"`
				User     string `json:"User"`
			}
			var list []psItem
			if json.Unmarshal(out, &list) == nil {
				for _, it := range list {
					upsertHost(it.IP, it.Hostname, it.MAC, it.Source, it.User)
				}
			} else {
				var single psItem
				if json.Unmarshal(out, &single) == nil && single.IP != "" {
					upsertHost(single.IP, single.Hostname, single.MAC, single.Source, single.User)
				}
			}
		}
	} else {
		// Linux ARP / ip neigh collection
		if out, err := exec.Command("ip", "-4", "neigh", "show").CombinedOutput(); err == nil {
			for _, line := range strings.Split(string(out), "\n") {
				fields := strings.Fields(line)
				if len(fields) >= 5 {
					ip := fields[0]
					mac := ""
					for idx, f := range fields {
						if f == "lladdr" && idx+1 < len(fields) {
							mac = fields[idx+1]
							break
						}
					}
					if mac != "" {
						upsertHost(ip, "", mac, "Tabela ARP", "")
					}
				}
			}
		}
	}

	// 3. Fast Concurrent Golang TCP Port Probe across the primary /24 subnet
	// Probes common computer ports (445 SMB, 3389 RDP, 135 RPC, 22 SSH, 9100 Printer)
	type portSpec struct {
		Port  int
		Label string
	}
	probePorts := []portSpec{
		{445, "SMB:445"},
		{3389, "RDP:3389"},
		{135, "RPC:135"},
		{22, "SSH:22"},
		{9100, "Print:9100"},
	}

	candidateIPs := make(map[string]bool)
	for ip := range hostMap {
		candidateIPs[ip] = true
	}
	if len(subnetPrefixes) > 0 {
		pref := subnetPrefixes[0]
		for hostNum := 1; hostNum <= 254; hostNum++ {
			ip := fmt.Sprintf("%s.%d", pref, hostNum)
			if !localIPs[ip] {
				candidateIPs[ip] = true
			}
		}
	}

	sem := make(chan struct{}, 64)
	var probeWg sync.WaitGroup

	for ip := range candidateIPs {
		probeWg.Add(1)
		go func(targetIP string) {
			defer probeWg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			openLabels := make([]string, 0)
			for _, ps := range probePorts {
				conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", targetIP, ps.Port), 220*time.Millisecond)
				if err == nil {
					_ = conn.Close()
					openLabels = append(openLabels, ps.Label)
				}
			}

			mu.Lock()
			_, alreadyInMap := hostMap[targetIP]
			mu.Unlock()

			if len(openLabels) == 0 && !alreadyInMap {
				return
			}

			resolvedName := ""
			if names, err := net.LookupAddr(targetIP); err == nil && len(names) > 0 {
				resolvedName = strings.TrimSuffix(names[0], ".")
			}

			src := ""
			if len(openLabels) > 0 {
				src = "Scanner LAN Go"
			}
			upsertHost(targetIP, resolvedName, "", src, "")

			mu.Lock()
			if entry, ok := hostMap[targetIP]; ok {
				entry.OpenServices = openLabels
				hasSMB := false
				hasRDP := false
				hasRPC := false
				hasSSH := false
				hasPrint := false
				for _, s := range openLabels {
					switch s {
					case "SMB:445":
						hasSMB = true
					case "RDP:3389":
						hasRDP = true
					case "RPC:135":
						hasRPC = true
					case "SSH:22":
						hasSSH = true
					case "Print:9100":
						hasPrint = true
					}
				}
				if hasPrint && !hasRPC && !hasRDP {
					entry.EstimatedType = "Impressora de Rede"
				} else if hasRDP || hasRPC || hasSMB || entry.SMBUser != "" {
					entry.EstimatedType = "Computador Windows"
				} else if hasSSH {
					entry.EstimatedType = "Servidor / Estação Linux"
				} else if entry.Hostname != "" {
					entry.EstimatedType = "Computador / Host"
				}
			}
			mu.Unlock()
		}(ip)
	}

	probeWg.Wait()

	// 4. Format and sort discovered hosts
	results := make([]DiscoveredLANHost, 0, len(hostMap))
	computersCount := 0
	for _, h := range hostMap {
		if strings.Contains(h.EstimatedType, "Computador") || strings.Contains(h.EstimatedType, "Linux") {
			computersCount++
		}
		results = append(results, *h)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].IPAddress < results[j].IPAddress
	})

	report.Hosts = results
	report.TotalFound = len(results)
	report.ComputersCount = computersCount
	report.DurationMs = time.Since(start).Milliseconds()
	return report
}
