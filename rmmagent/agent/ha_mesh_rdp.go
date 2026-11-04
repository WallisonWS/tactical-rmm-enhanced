package agent

import (
	"crypto/tls"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"

	ps "github.com/elastic/go-sysinfo"
	trmm "github.com/wh1te909/trmm-shared"
)

// HALinkHealthReport represents the enterprise High-Availability health status
// between the Agent, Tactical API, NATS Broker, and MeshCentral service.
type HALinkHealthReport struct {
	AgentID           string   `json:"agent_id"`
	Hostname          string   `json:"hostname"`
	Platform          string   `json:"platform"`
	AgentVersion      string   `json:"agent_version"`
	APIReachable      bool     `json:"api_reachable"`
	APILatencyMs      int64    `json:"api_latency_ms"`
	NATSReachable     bool     `json:"nats_reachable"`
	NATSLatencyMs     int64    `json:"nats_latency_ms"`
	NATSTransport     string   `json:"nats_transport"`
	MeshServiceStatus string   `json:"mesh_service_status"`
	MeshHealthy       bool     `json:"mesh_healthy"`
	MeshBinaryExists  bool     `json:"mesh_binary_exists"`
	MeshProcessCount  int      `json:"mesh_process_count"`
	MeshNodeID        string   `json:"mesh_node_id"`
	ProxyConfigured   bool     `json:"proxy_configured"`
	ProxyURL          string   `json:"proxy_url"`
	OverallStatus     string   `json:"overall_status"`
	Recommendations   []string `json:"recommendations"`
	Timestamp         string   `json:"timestamp"`
}

// RDPSessionInfo represents an active or disconnected OS user session.
type RDPSessionInfo struct {
	SessionName string `json:"session_name"`
	Username    string `json:"username"`
	ID          string `json:"id"`
	State       string `json:"state"`
}

// CorporateRDPStatus represents the state of Remote Desktop Services on the endpoint.
type CorporateRDPStatus struct {
	Platform       string           `json:"platform"`
	RDPEnabled     bool             `json:"rdp_enabled"`
	NLAEnabled     bool             `json:"nla_enabled"`
	ServiceStatus  string           `json:"service_status"`
	ListeningPort  int              `json:"listening_port"`
	PortReachable  bool             `json:"port_reachable"`
	LocalIPs       []string         `json:"local_ips"`
	ActiveSessions []RDPSessionInfo `json:"active_sessions"`
	Timestamp      string           `json:"timestamp"`
}

func countMeshProcesses() int {
	count := 0
	procs, err := ps.Processes()
	if err != nil {
		return 0
	}
	for _, process := range procs {
		p, err := process.Info()
		if err != nil {
			continue
		}
		if strings.Contains(strings.ToLower(p.Name), "meshagent") {
			count++
		}
	}
	return count
}

// CheckLinkAndMeshHealth validates continuous connectivity across API, NATS, and MeshCentral.
func (a *Agent) CheckLinkAndMeshHealth() HALinkHealthReport {
	hostname, _ := os.Hostname()
	if hostname == "" {
		hostname = a.Hostname
	}
	report := HALinkHealthReport{
		AgentID:          a.AgentID,
		Hostname:         hostname,
		Platform:         runtime.GOOS,
		AgentVersion:     a.Version,
		MeshBinaryExists: trmm.FileExists(a.MeshSystemEXE),
		MeshProcessCount: countMeshProcesses(),
		Recommendations:  []string{},
		Timestamp:        time.Now().UTC().Format(time.RFC3339),
	}

	// 1. Check corporate proxy environment
	if a.Proxy != "" {
		report.ProxyConfigured = true
		report.ProxyURL = a.Proxy
	} else {
		for _, envKey := range []string{"HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"} {
			if val := os.Getenv(envKey); val != "" {
				report.ProxyConfigured = true
				report.ProxyURL = val
				break
			}
		}
	}

	// 2. Check API HTTPS reachability & latency (respecting Insecure/Cert settings)
	targetURL := a.BaseURL
	if targetURL == "" && a.ApiURL != "" {
		if strings.HasPrefix(a.ApiURL, "http://") || strings.HasPrefix(a.ApiURL, "https://") {
			targetURL = a.ApiURL
		} else {
			targetURL = "https://" + a.ApiURL
		}
	}
	if targetURL != "" {
		start := time.Now()
		tr := &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: a.Insecure},
		}
		client := &http.Client{Timeout: 5 * time.Second, Transport: tr}
		resp, err := client.Get(targetURL)
		if err == nil {
			report.APIReachable = true
			report.APILatencyMs = time.Since(start).Milliseconds()
			resp.Body.Close()
		} else {
			report.Recommendations = append(report.Recommendations, fmt.Sprintf("Falha ao contatar API (%s): verifique DNS e saída HTTPS (443).", targetURL))
		}
	}

	// 3. Check NATS WebSocket (wss://443) or TCP (tls://4222) reachability & latency
	natsTarget := a.NatsServer
	if natsTarget == "" && a.ApiURL != "" {
		natsTarget = fmt.Sprintf("wss://%s:443", a.ApiURL)
	}
	if natsTarget != "" {
		if strings.HasPrefix(natsTarget, "wss://") {
			report.NATSTransport = "WebSocket TLS (wss://443)"
		} else {
			report.NATSTransport = "Native TLS (tls://4222)"
		}
		natsHost := strings.TrimPrefix(natsTarget, "wss://")
		natsHost = strings.TrimPrefix(natsHost, "ws://")
		natsHost = strings.TrimPrefix(natsHost, "tls://")
		natsHost = strings.TrimPrefix(natsHost, "nats://")
		if idx := strings.Index(natsHost, "/"); idx != -1 {
			natsHost = natsHost[:idx]
		}
		if !strings.Contains(natsHost, ":") {
			natsHost = natsHost + ":443"
		}
		start := time.Now()
		conn, err := net.DialTimeout("tcp", natsHost, 4*time.Second)
		if err == nil {
			report.NATSReachable = true
			report.NATSLatencyMs = time.Since(start).Milliseconds()
			conn.Close()
		} else {
			report.Recommendations = append(report.Recommendations, fmt.Sprintf("Endpoint do Broker NATS (%s) inacessível: valide liberação TCP na rede corporativa.", natsHost))
		}
	}

	// 4. Check MeshCentral Agent service health & NodeID synchronization
	if runtime.GOOS == "windows" {
		out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"(Get-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue).Status").CombinedOutput()
		status := strings.TrimSpace(string(out))
		if err == nil && status != "" {
			report.MeshServiceStatus = status
			report.MeshHealthy = strings.EqualFold(status, "Running")
		} else {
			report.MeshServiceStatus = "NotInstalledOrStopped"
			report.MeshHealthy = false
		}
	} else {
		out, err := exec.Command("systemctl", "is-active", "meshagent").CombinedOutput()
		status := strings.TrimSpace(string(out))
		if err == nil && status == "active" {
			report.MeshServiceStatus = "Running"
			report.MeshHealthy = true
		} else {
			report.MeshServiceStatus = status
			if report.MeshServiceStatus == "" {
				report.MeshServiceStatus = "Inactive"
			}
			report.MeshHealthy = false
		}
	}

	if report.MeshBinaryExists {
		if nodeID, err := a.getMeshNodeID(); err == nil && nodeID != "" {
			report.MeshNodeID = StripAll(nodeID)
		}
	}

	if report.MeshProcessCount > 3 {
		report.Recommendations = append(report.Recommendations, fmt.Sprintf("Detectados %d processos meshagent simultâneos (possível conflito de processo órfão). Execute 'Reparar Mesh & Link' para limpar.", report.MeshProcessCount))
	}

	if !report.MeshHealthy || report.MeshNodeID == "" {
		report.MeshHealthy = false
		report.Recommendations = append(report.Recommendations, "Serviço Mesh Agent inativo ou NodeID dessincronizado. Execute 'Reparar Mesh & Link' para restaurar e ressincronizar automaticamente.")
	}

	if report.APIReachable && report.NATSReachable && report.MeshHealthy {
		report.OverallStatus = "HEALTHY"
	} else if report.APIReachable || report.NATSReachable {
		report.OverallStatus = "DEGRADED"
	} else {
		report.OverallStatus = "CRITICAL"
	}

	return report
}

// RepairMeshAndLink resolves conflicts between Agent and MeshAgent, cleans orphan processes,
// restarts MeshAgent, flushes DNS, and resynchronizes MeshNodeID with the Tactical API.
func (a *Agent) RepairMeshAndLink() map[string]interface{} {
	actions := []string{}
	success := true

	if runtime.GOOS == "windows" {
		// 1. Flush DNS to ensure fresh resolution of API/Mesh FQDNs
		_ = exec.Command("ipconfig", "/flushdns").Run()
		actions = append(actions, "Cache DNS corporativo atualizado (ipconfig /flushdns)")

		// 2. Stop service and clean any conflicting/zombie meshagent processes if stuck
		_ = exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"Stop-Service -Name 'Mesh Agent' -Force -ErrorAction SilentlyContinue").Run()
		if countMeshProcesses() > 0 {
			a.ForceKillMesh()
			actions = append(actions, "Processos Mesh Agent órfãos/conflitantes encerrados com segurança")
		}

		// 3. Start Mesh Agent service cleanly
		err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"Set-Service -Name 'Mesh Agent' -StartupType Automatic -ErrorAction SilentlyContinue; Start-Service -Name 'Mesh Agent' -ErrorAction Stop").Run()
		if err != nil {
			_ = exec.Command("sc.exe", "start", "Mesh Agent").Run()
			actions = append(actions, "Solicitada inicialização do serviço 'Mesh Agent' via SCM")
		} else {
			actions = append(actions, "Serviço 'Mesh Agent' reiniciado sem conflitos")
		}
	} else {
		_ = exec.Command("resolvectl", "flush-caches").Run()
		_ = exec.Command("systemctl", "stop", "meshagent").Run()
		if countMeshProcesses() > 0 {
			a.ForceKillMesh()
		}
		_ = exec.Command("systemctl", "restart", "meshagent").Run()
		actions = append(actions, "Serviço systemd 'meshagent' reiniciado e processos órfãos limpos")
	}

	time.Sleep(2 * time.Second)

	// 4. Synchronize MeshNodeID with Tactical RMM API & MeshCentral Server
	a.SyncMeshNodeID(true)
	actions = append(actions, "MeshNodeID ressincronizado com a API e MeshCentral (/api/v3/syncmesh/)")

	health := a.CheckLinkAndMeshHealth()
	return map[string]interface{}{
		"success":       success,
		"mesh_node_id":  health.MeshNodeID,
		"actions_taken": actions,
		"health_after":  health,
		"timestamp":     time.Now().UTC().Format(time.RFC3339),
	}
}

// GetRDPStatusAndSessions inspects Remote Desktop configuration, NLA enforcement, and active user sessions.
func (a *Agent) GetRDPStatusAndSessions() CorporateRDPStatus {
	status := CorporateRDPStatus{
		Platform:       runtime.GOOS,
		ListeningPort:  3389,
		LocalIPs:       []string{},
		ActiveSessions: []RDPSessionInfo{},
		Timestamp:      time.Now().UTC().Format(time.RFC3339),
	}

	// Collect local IPv4 addresses
	addrs, err := net.InterfaceAddrs()
	if err == nil {
		for _, addr := range addrs {
			if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
				status.LocalIPs = append(status.LocalIPs, ipnet.IP.String())
			}
		}
	}

	if runtime.GOOS == "windows" {
		// Check TermService status
		svcOut, _ := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"(Get-Service -Name 'TermService' -ErrorAction SilentlyContinue).Status").CombinedOutput()
		status.ServiceStatus = strings.TrimSpace(string(svcOut))
		if status.ServiceStatus == "" {
			status.ServiceStatus = "Unknown"
		}

		// Check fDenyTSConnections (0 = RDP enabled, 1 = disabled)
		denyOut, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"(Get-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -ErrorAction SilentlyContinue).fDenyTSConnections").CombinedOutput()
		if err == nil && strings.TrimSpace(string(denyOut)) == "0" {
			status.RDPEnabled = true
		}

		// Check NLA UserAuthentication (1 = NLA enabled)
		nlaOut, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"(Get-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' -Name 'UserAuthentication' -ErrorAction SilentlyContinue).UserAuthentication").CombinedOutput()
		if err == nil && strings.TrimSpace(string(nlaOut)) == "1" {
			status.NLAEnabled = true
		}

		// Check custom RDP port
		portOut, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
			"(Get-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' -Name 'PortNumber' -ErrorAction SilentlyContinue).PortNumber").CombinedOutput()
		if err == nil {
			if p, convErr := strconv.Atoi(strings.TrimSpace(string(portOut))); convErr == nil && p > 0 {
				status.ListeningPort = p
			}
		}

		// Parse active sessions via qwinsta
		qwOut, err := exec.Command("qwinsta").CombinedOutput()
		if err == nil {
			lines := strings.Split(string(qwOut), "\n")
			for i, line := range lines {
				if i == 0 || strings.TrimSpace(line) == "" {
					continue
				}
				fields := strings.Fields(strings.TrimPrefix(line, ">"))
				if len(fields) >= 3 {
					sess := RDPSessionInfo{
						SessionName: fields[0],
					}
					if len(fields) >= 4 {
						sess.Username = fields[1]
						sess.ID = fields[2]
						sess.State = fields[3]
					} else {
						sess.Username = "-"
						sess.ID = fields[1]
						sess.State = fields[2]
					}
					status.ActiveSessions = append(status.ActiveSessions, sess)
				}
			}
		}
	} else {
		// Linux xrdp check
		out, err := exec.Command("systemctl", "is-active", "xrdp").CombinedOutput()
		if err == nil && strings.TrimSpace(string(out)) == "active" {
			status.ServiceStatus = "Running"
			status.RDPEnabled = true
		} else {
			status.ServiceStatus = "Stopped"
		}
		whoOut, err := exec.Command("who").CombinedOutput()
		if err == nil {
			for idx, line := range strings.Split(string(whoOut), "\n") {
				fields := strings.Fields(line)
				if len(fields) >= 2 {
					status.ActiveSessions = append(status.ActiveSessions, RDPSessionInfo{
						SessionName: fields[1],
						Username:    fields[0],
						ID:          strconv.Itoa(idx + 1),
						State:       "Active",
					})
				}
			}
		}
	}

	// Test local TCP port listener
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", status.ListeningPort), 1500*time.Millisecond)
	if err == nil {
		status.PortReachable = true
		conn.Close()
	}

	return status
}

// ManageCorporateRDP configures Remote Desktop settings, NLA security, or session state.
func (a *Agent) ManageCorporateRDP(action string, enforceNLA bool, sessionID string) map[string]interface{} {
	steps := []string{}
	success := true
	errMsg := ""

	if runtime.GOOS == "windows" {
		switch action {
		case "enable_rdp":
			nlaVal := 0
			if enforceNLA {
				nlaVal = 1
			}
			psCmd := fmt.Sprintf(
				"Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 0; "+
					"Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' -Name 'UserAuthentication' -Value %d; "+
					"Set-Service -Name 'TermService' -StartupType Automatic; Start-Service -Name 'TermService'; "+
					"Enable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue",
				nlaVal,
			)
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			if err != nil {
				success = false
				errMsg = string(out)
			} else {
				steps = append(steps, fmt.Sprintf("RDP corporativo habilitado (NLA=%v) e serviço TermService iniciado", enforceNLA))
			}

		case "disable_rdp":
			psCmd := "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 1; " +
				"Disable-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue"
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", psCmd).CombinedOutput()
			if err != nil {
				success = false
				errMsg = string(out)
			} else {
				steps = append(steps, "Conexões RDP externas desabilitadas com segurança")
			}

		case "restart_rdp":
			out, err := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command",
				"Restart-Service -Name 'TermService' -Force").CombinedOutput()
			if err != nil {
				success = false
				errMsg = string(out)
			} else {
				steps = append(steps, "Serviço TermService reiniciado com sucesso")
			}

		case "logoff_session":
			if sessionID != "" {
				out, err := exec.Command("logoff", sessionID).CombinedOutput()
				if err != nil {
					success = false
					errMsg = string(out)
				} else {
					steps = append(steps, fmt.Sprintf("Sessão ID %s encerrada com sucesso", sessionID))
				}
			}
		}
	} else {
		switch action {
		case "enable_rdp":
			_ = exec.Command("systemctl", "enable", "--now", "xrdp").Run()
			steps = append(steps, "Serviço xrdp habilitado e iniciado")
		case "disable_rdp":
			_ = exec.Command("systemctl", "disable", "--now", "xrdp").Run()
			steps = append(steps, "Serviço xrdp desabilitado")
		case "restart_rdp":
			_ = exec.Command("systemctl", "restart", "xrdp").Run()
			steps = append(steps, "Serviço xrdp reiniciado")
		}
	}

	return map[string]interface{}{
		"success":    success,
		"action":     action,
		"steps":      steps,
		"error":      errMsg,
		"rdp_status": a.GetRDPStatusAndSessions(),
		"timestamp":  time.Now().UTC().Format(time.RFC3339),
	}
}
