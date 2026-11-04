package agent

import (
	"fmt"
	"net"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

type NetConnectionInfo struct {
	Protocol   string `json:"protocol"`
	LocalAddr  string `json:"local_addr"`
	LocalPort  int    `json:"local_port"`
	RemoteAddr string `json:"remote_addr"`
	RemotePort int    `json:"remote_port"`
	State      string `json:"state"`
	PID        int32  `json:"pid"`
	Process    string `json:"process"`
}

type PortScanResult struct {
	Host       string        `json:"host"`
	OpenPorts  []OpenPortRec `json:"open_ports"`
	ScannedCnt int           `json:"scanned_count"`
	DurationMs int64         `json:"duration_ms"`
}

type OpenPortRec struct {
	Port      int    `json:"port"`
	Protocol  string `json:"protocol"`
	Service   string `json:"service"`
	LatencyMs int64  `json:"latency_ms"`
	Banner    string `json:"banner,omitempty"`
}

type NetDiagReport struct {
	Target          string   `json:"target"`
	DNSResolvedIPs  []string `json:"dns_resolved_ips"`
	DNSLatencyMs    int64    `json:"dns_latency_ms"`
	PingSuccess     bool     `json:"ping_success"`
	PingOutput      string   `json:"ping_output"`
	TCP80Reachable  bool     `json:"tcp_80_reachable"`
	TCP443Reachable bool     `json:"tcp_443_reachable"`
	LocalIPs        []string `json:"local_ips"`
	PublicIP        string   `json:"public_ip"`
	Timestamp       string   `json:"timestamp"`
}

var commonPortServices = map[int]string{
	21:    "FTP",
	22:    "SSH",
	23:    "Telnet",
	25:    "SMTP",
	53:    "DNS",
	80:    "HTTP",
	110:   "POP3",
	135:   "RPC",
	139:   "NetBIOS",
	143:   "IMAP",
	389:   "LDAP",
	443:   "HTTPS",
	445:   "SMB",
	1433:  "MSSQL",
	1521:  "Oracle",
	3306:  "MySQL",
	3389:  "RDP",
	4222:  "NATS",
	5432:  "PostgreSQL",
	5900:  "VNC",
	5985:  "WinRM-HTTP",
	5986:  "WinRM-HTTPS",
	6379:  "Redis",
	8080:  "HTTP-Alt",
	8443:  "HTTPS-Alt",
	27017: "MongoDB",
}

// GetActiveConnections retrieves active TCP/UDP network connections and owning PIDs across Windows, Linux, and macOS.
func (a *Agent) GetActiveConnections() []NetConnectionInfo {
	results := make([]NetConnectionInfo, 0)

	var out [2]string
	var err error
	if runtime.GOOS == "windows" {
		out, err = CMD("netstat.exe", []string{"-ano"}, 15, false)
	} else {
		out, err = CMD("ss", []string{"-tulnp"}, 15, false)
		if err != nil || out[0] == "" {
			out, err = CMD("netstat", []string{"-tulnp"}, 15, false)
		}
	}
	if err != nil {
		a.Logger.Debugln("GetActiveConnections error:", err)
		return results
	}

	procMap := make(map[int32]string)
	for _, p := range a.GetProcsRPC() {
		procMap[p.PID] = p.Name
	}

	lines := strings.Split(out[0], "\n")
	for _, rawLine := range lines {
		line := strings.TrimSpace(rawLine)
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 4 {
			continue
		}
		proto := strings.ToUpper(fields[0])
		if proto != "TCP" && proto != "UDP" && !strings.HasPrefix(proto, "TCP") && !strings.HasPrefix(proto, "UDP") {
			continue
		}

		localHost, localPort := splitAddrPort(fields[1])
		remoteHost, remotePort := splitAddrPort(fields[2])
		state := "STATELESS"
		var pid int32

		if strings.HasPrefix(proto, "TCP") && len(fields) >= 5 {
			state = fields[3]
			pVal, _ := strconv.Atoi(fields[4])
			pid = int32(pVal)
		} else if len(fields) >= 4 {
			pVal, _ := strconv.Atoi(fields[len(fields)-1])
			pid = int32(pVal)
		}

		procName := procMap[pid]
		if procName == "" && pid == 0 {
			procName = "System Idle"
		} else if procName == "" && pid == 4 {
			procName = "System"
		}

		results = append(results, NetConnectionInfo{
			Protocol:   proto,
			LocalAddr:  localHost,
			LocalPort:  localPort,
			RemoteAddr: remoteHost,
			RemotePort: remotePort,
			State:      state,
			PID:        pid,
			Process:    procName,
		})
	}

	return results
}

func splitAddrPort(input string) (string, int) {
	input = strings.TrimSpace(input)
	if input == "*:*" || input == "0.0.0.0:*" || input == "[::]:*" {
		return "*", 0
	}
	lastColon := strings.LastIndex(input, ":")
	if lastColon == -1 {
		return input, 0
	}
	host := input[:lastColon]
	portStr := input[lastColon+1:]
	port, _ := strconv.Atoi(portStr)
	return host, port
}

// RunPortScan performs a concurrent TCP port scan against a target host and list of ports (or default common ports).
func (a *Agent) RunPortScan(host string, portsSpec string, timeoutMs int) PortScanResult {
	start := time.Now()
	if strings.TrimSpace(host) == "" {
		host = "127.0.0.1"
	}
	if timeoutMs <= 0 || timeoutMs > 5000 {
		timeoutMs = 600
	}

	ports := parsePortSpec(portsSpec)
	var wg sync.WaitGroup
	var mu sync.Mutex
	openPorts := make([]OpenPortRec, 0)
	sem := make(chan struct{}, 64)

	for _, port := range ports {
		wg.Add(1)
		go func(p int) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			target := net.JoinHostPort(host, strconv.Itoa(p))
			t0 := time.Now()
			conn, err := net.DialTimeout("tcp", target, time.Duration(timeoutMs)*time.Millisecond)
			if err != nil {
				return
			}
			latency := time.Since(t0).Milliseconds()
			_ = conn.Close()

			svcName := commonPortServices[p]
			if svcName == "" {
				svcName = "tcp-service"
			}

			mu.Lock()
			openPorts = append(openPorts, OpenPortRec{
				Port:      p,
				Protocol:  "TCP",
				Service:   svcName,
				LatencyMs: latency,
			})
			mu.Unlock()
		}(port)
	}

	wg.Wait()
	sort.Slice(openPorts, func(i, j int) bool {
		return openPorts[i].Port < openPorts[j].Port
	})

	return PortScanResult{
		Host:       host,
		OpenPorts:  openPorts,
		ScannedCnt: len(ports),
		DurationMs: time.Since(start).Milliseconds(),
	}
}

func parsePortSpec(spec string) []int {
	spec = strings.TrimSpace(spec)
	if spec == "" {
		defaults := make([]int, 0, len(commonPortServices))
		for p := range commonPortServices {
			defaults = append(defaults, p)
		}
		sort.Ints(defaults)
		return defaults
	}

	seen := make(map[int]bool)
	result := make([]int, 0)
	parts := strings.Split(spec, ",")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if strings.Contains(part, "-") {
			bounds := strings.SplitN(part, "-", 2)
			startP, err1 := strconv.Atoi(strings.TrimSpace(bounds[0]))
			endP, err2 := strconv.Atoi(strings.TrimSpace(bounds[1]))
			if err1 == nil && err2 == nil && startP > 0 && endP >= startP && (endP-startP) <= 2048 {
				for p := startP; p <= endP; p++ {
					if p <= 65535 && !seen[p] {
						seen[p] = true
						result = append(result, p)
					}
				}
			}
		} else {
			p, err := strconv.Atoi(part)
			if err == nil && p > 0 && p <= 65535 && !seen[p] {
				seen[p] = true
				result = append(result, p)
			}
		}
	}
	sort.Ints(result)
	return result
}

// RunNetworkDiagnostics executes DNS, ICMP Ping, and TCP 80/443 reachability diagnostics.
func (a *Agent) RunNetworkDiagnostics(target string) NetDiagReport {
	if strings.TrimSpace(target) == "" {
		target = "1.1.1.1"
	}

	report := NetDiagReport{
		Target:    target,
		PublicIP:  a.PublicIP(),
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	if addrs, err := net.InterfaceAddrs(); err == nil {
		for _, addr := range addrs {
			if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
				report.LocalIPs = append(report.LocalIPs, ipnet.IP.String())
			}
		}
	}

	dnsStart := time.Now()
	ips, err := net.LookupHost(target)
	report.DNSLatencyMs = time.Since(dnsStart).Milliseconds()
	if err == nil {
		report.DNSResolvedIPs = ips
	}

	pingRes, pingErr := DoPing(target)
	if pingErr == nil {
		report.PingSuccess = pingRes.Status == "passing"
		report.PingOutput = pingRes.Output
	} else {
		report.PingSuccess = false
		report.PingOutput = fmt.Sprintf("ping error: %v", pingErr)
	}

	if c80, err := net.DialTimeout("tcp", net.JoinHostPort(target, "80"), 1500*time.Millisecond); err == nil {
		report.TCP80Reachable = true
		_ = c80.Close()
	}
	if c443, err := net.DialTimeout("tcp", net.JoinHostPort(target, "443"), 1500*time.Millisecond); err == nil {
		report.TCP443Reachable = true
		_ = c443.Close()
	}

	return report
}
