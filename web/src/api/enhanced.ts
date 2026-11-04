import axios from "axios";

// ============================================================================
// Enhanced Tactical RMM API Client (Telemetry, Security/EDR, Network, Self-Heal, Winget, AI & Fleet KPIs)
// ============================================================================

export interface LiveTelemetrySnapshot {
  agent_id: string;
  hostname: string;
  platform: string;
  architecture?: string;
  cpu_load_percent: number;
  cpu_per_core?: number[];
  cpu_cores_logical?: number;
  ram_total_mb: number;
  ram_used_mb: number;
  ram_free_mb: number;
  ram_used_percent: number;
  disk_metrics?: Array<{
    mountpoint: string;
    fstype: string;
    total_gb: number;
    used_gb: number;
    free_gb: number;
    used_percent: number;
  }>;
  net_bytes_sent?: number;
  net_bytes_recv?: number;
  smart_health?: Array<{
    model: string;
    serial_number: string;
    status: string;
    media_type: string;
  }>;
  uptime_seconds?: number;
  needs_reboot: boolean;
  process_count?: number;
  cached_fallback?: boolean;
  timestamp?: string;
}

export interface SecurityAuditReport {
  agent_id: string;
  hostname: string;
  platform: string;
  security_score: number;
  antivirus_enabled: boolean;
  antivirus_name: string;
  realtime_protection: boolean;
  firewall_enabled: boolean;
  firewall_profiles: Array<{ name: string; enabled: boolean }>;
  disk_encrypted: boolean;
  encryption_detail: string;
  uac_enabled: boolean;
  rdp_enabled: boolean;
  smbv1_enabled: boolean;
  suspicious_processes: Array<{
    pid: number;
    name: string;
    reason: string;
    mem_mb: number;
    cpu_pct: string;
  }>;
  high_risk_open_ports: number[];
  local_admins: string[];
  startup_items_count: number;
  recommendations: string[];
  timestamp: string;
}

export interface NetConnectionInfo {
  protocol: string;
  local_addr: string;
  local_port: number;
  remote_addr: string;
  remote_port: number;
  state: string;
  pid: number;
  process: string;
}

export interface PortScanResult {
  host: string;
  open_ports: Array<{
    port: number;
    protocol: string;
    service: string;
    latency_ms: number;
  }>;
  scanned_count: number;
  duration_ms: number;
}

export interface NetDiagReport {
  target: string;
  dns_resolved_ips: string[];
  dns_latency_ms: number;
  ping_success: boolean;
  ping_output: string;
  tcp_80_reachable: boolean;
  tcp_443_reachable: boolean;
  local_ips: string[];
  public_ip: string;
  timestamp: string;
}

export interface FleetExecutiveSummary {
  total_agents: number;
  online_agents: number;
  offline_agents: number;
  overdue_agents: number;
  reboot_needed_agents: number;
  maintenance_agents: number;
  availability_percent: number;
  patch_compliance_percent: number;
  fleet_health_score: number;
  active_alerts: {
    total: number;
    error: number;
    warning: number;
  };
  failing_checks_count: number;
  agents_with_pending_patches: number;
  timestamp: string;
}

export async function fetchFleetExecutiveSummary(): Promise<FleetExecutiveSummary> {
  const { data } = await axios.get("/agents/executive-summary/");
  return data;
}

export async function fetchAgentLiveTelemetry(agentId: string): Promise<LiveTelemetrySnapshot> {
  const { data } = await axios.get(`/agents/${agentId}/telemetry/`);
  return data;
}

export async function fetchAgentSecurityAudit(agentId: string): Promise<SecurityAuditReport> {
  const { data } = await axios.get(`/agents/${agentId}/security-audit/`);
  return data;
}

export async function queryAgentSecurityDetails(
  agentId: string,
  queryType: "startup_items" | "local_users" | "bitlocker_status",
) {
  const { data } = await axios.post(`/agents/${agentId}/security-audit/`, {
    query_type: queryType,
  });
  return data;
}

export async function fetchAgentFirewallStatus(agentId: string) {
  const { data } = await axios.get(`/agents/${agentId}/firewall/`);
  return data;
}

export async function executeAgentFirewallRule(
  agentId: string,
  payload: {
    action: "enable_all" | "disable_all" | "block_port" | "allow_port" | "delete_rule";
    rule_name?: string;
    direction?: "in" | "out";
    protocol?: "TCP" | "UDP";
    port?: string;
    remote_ip?: string;
  },
) {
  const { data } = await axios.post(`/agents/${agentId}/firewall/`, payload);
  return data;
}

export async function fetchAgentNetConnections(agentId: string): Promise<NetConnectionInfo[]> {
  const { data } = await axios.get(`/agents/${agentId}/network/`);
  return data;
}

export async function runAgentPortScan(
  agentId: string,
  host: string,
  ports = "",
  timeoutMs = 600,
): Promise<PortScanResult> {
  const { data } = await axios.post(`/agents/${agentId}/network/`, {
    tool: "portscan",
    host,
    ports,
    timeout_ms: timeoutMs,
  });
  return data;
}

export async function runAgentNetDiag(
  agentId: string,
  target = "1.1.1.1",
): Promise<NetDiagReport> {
  const { data } = await axios.post(`/agents/${agentId}/network/`, {
    tool: "netdiag",
    target,
  });
  return data;
}

export async function triggerAgentSelfHeal(
  agentId: string,
  action: "self_heal" | "disk_cleanup" | "trim_memory" | "reset_network" = "self_heal",
  mode: "full" | "disk" | "services" | "network" | "winupdate" | "memory" = "full",
  fullReset = false,
) {
  const { data } = await axios.post(`/agents/${agentId}/self-heal/`, {
    action,
    mode,
    full_reset: fullReset,
  });
  return data;
}

export async function fetchAgentWingetPackages(agentId: string) {
  const { data } = await axios.get(`/agents/${agentId}/winget/`);
  return data;
}

export async function runAgentWingetOperation(
  agentId: string,
  operation: "install" | "upgrade",
  packageId = "all",
) {
  const { data } = await axios.post(`/agents/${agentId}/winget/`, {
    operation,
    package_id: packageId,
  });
  return data;
}

export async function runAgentAIDiagnostics(agentId: string) {
  const { data } = await axios.post(`/agents/${agentId}/ai-diagnostics/`);
  return data;
}
