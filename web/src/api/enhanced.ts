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

export interface HALinkHealthReport {
  agent_id: string;
  hostname: string;
  platform: string;
  agent_version?: string;
  api_reachable: boolean;
  api_latency_ms: number;
  nats_reachable: boolean;
  nats_latency_ms: number;
  nats_transport?: string;
  mesh_service_status: string;
  mesh_healthy: boolean;
  mesh_binary_exists?: boolean;
  mesh_process_count?: number;
  mesh_node_id?: string;
  mesh_id_synced?: boolean;
  proxy_configured: boolean;
  proxy_url: string;
  overall_status: "HEALTHY" | "DEGRADED" | "CRITICAL";
  recommendations: string[];
  timestamp: string;
}

export interface RDPSessionInfo {
  session_name: string;
  username: string;
  id: string;
  state: string;
}

export interface CorporateRDPStatus {
  hostname?: string;
  public_ip?: string;
  platform: string;
  rdp_enabled: boolean;
  nla_enabled: boolean;
  service_status: string;
  listening_port: number;
  port_reachable: boolean;
  local_ips: string[];
  active_sessions: RDPSessionInfo[];
  timestamp: string;
}

export async function fetchAgentHALinkHealth(agentId: string): Promise<HALinkHealthReport> {
  const { data } = await axios.get(`/agents/${agentId}/ha-link/`);
  return data;
}

export async function repairAgentHALink(agentId: string) {
  const { data } = await axios.post(`/agents/${agentId}/ha-link/`);
  return data;
}

export async function fetchAgentRDPStatus(agentId: string): Promise<CorporateRDPStatus> {
  const { data } = await axios.get(`/agents/${agentId}/rdp/`);
  return data;
}

export async function manageAgentRDP(
  agentId: string,
  action: "enable_rdp" | "disable_rdp" | "restart_rdp" | "logoff_session",
  enforceNLA = true,
  sessionId = "",
) {
  const { data } = await axios.post(`/agents/${agentId}/rdp/`, {
    action,
    enforce_nla: enforceNLA,
    session_id: sessionId,
  });
  return data;
}

export function downloadNativeRDPFile(hostname: string, hostAddress: string, port = 3389) {
  const rdpContent = [
    `full address:s:${hostAddress}:${port}`,
    "prompt for credentials:i:1",
    "administrative session:i:1",
    "screen mode id:i:2",
    "use multimon:i:0",
    "desktopwidth:i:1920",
    "desktopheight:i:1080",
    "session bpp:i:32",
    "compression:i:1",
    "keyboardhook:i:2",
    "audiocapturemode:i:0",
    "videoplaybackmode:i:1",
    "connection type:i:7",
    "networkautodetect:i:1",
    "bandwidthautodetect:i:1",
    "enableworkspacereconnect:i:1",
    "enablecredsspsupport:i:1",
    "authentication level:i:2",
    "autoreconnection enabled:i:1",
  ].join("\r\n");

  const blob = new Blob([rdpContent], { type: "application/x-rdp;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${hostname || hostAddress}.rdp`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export interface HardwareDomainInventory {
  hostname: string;
  platform: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  bios_version: string;
  domain_or_workgroup: string;
  part_of_domain: boolean;
  entra_id_joined: boolean;
  active_power_plan: string;
  gpus: string[];
  battery_present: boolean;
  battery_charge_pct: number;
  battery_status: string;
  printers_count: number;
  restore_points_count: number;
  timestamp: string;
}

export interface PrinterInfo {
  name: string;
  driver_name: string;
  port_name: string;
  printer_status: string;
  shared: boolean;
  job_count: number;
}

export interface RestorePointInfo {
  sequence_number: number;
  description: string;
  creation_time: string;
  event_type: string;
}

export async function fetchAgentHardwareInventory(
  agentId: string,
): Promise<HardwareDomainInventory> {
  const { data } = await axios.get(`/agents/${agentId}/hardware-inventory/`);
  return data;
}

export async function runAgentAdminAction(
  agentId: string,
  action: "gpupdate_force" | "high_performance_power" | "sync_time" | "clear_print_spooler",
) {
  const { data } = await axios.post(`/agents/${agentId}/hardware-inventory/`, {
    action,
  });
  return data;
}

export async function fetchAgentPrinters(agentId: string): Promise<PrinterInfo[]> {
  const { data } = await axios.get(`/agents/${agentId}/printers/`);
  return data;
}

export async function runAgentPrinterAction(
  agentId: string,
  action: "clear_queue" | "set_default" | "test_page",
  printerName: string,
) {
  const { data } = await axios.post(`/agents/${agentId}/printers/`, {
    action,
    printer_name: printerName,
  });
  return data;
}

export async function fetchAgentRestorePoints(
  agentId: string,
): Promise<{ restore_points: RestorePointInfo[] }> {
  const { data } = await axios.get(`/agents/${agentId}/it-support/`);
  return data;
}

export async function createAgentRestorePoint(agentId: string, description: string) {
  const { data } = await axios.post(`/agents/${agentId}/it-support/`, {
    tool_type: "system_restore",
    description,
  });
  return data;
}

export async function sendAgentITSupportMessage(
  agentId: string,
  title: string,
  message: string,
  timeoutSec = 60,
) {
  const { data } = await axios.post(`/agents/${agentId}/it-support/`, {
    tool_type: "broadcast_msg",
    title,
    message,
    timeout_sec: timeoutSec,
  });
  return data;
}

export interface WindowsServerADProfile {
  hostname: string;
  platform: string;
  os_caption: string;
  os_version: string;
  environment_mode: "active_directory" | "workgroup_standalone" | "linux_standalone";
  is_windows_server: boolean;
  is_domain_controller: boolean;
  part_of_domain: boolean;
  domain_name: string;
  workgroup_name: string;
  forest_name: string;
  domain_role_id: number;
  domain_role_label: string;
  domain_controller_name: string;
  domain_controller_address: string;
  ad_site_name: string;
  computer_dn: string;
  organizational_unit: string;
  secure_channel_valid: boolean;
  sysvol_reachable: boolean;
  netlogon_reachable: boolean;
  time_sync_source: string;
  deployed_via_gpo: boolean;
  deployment_mode: string;
  last_gpo_verify: string;
  applied_computer_gpos: string[];
  installed_server_roles: string[];
  ad_critical_services: Record<string, string>;
  recommended_agent_type: string;
  client_id?: number;
  client_name?: string;
  site_id?: number;
  site_name?: string;
  timestamp: string;
}

export async function fetchAgentADServerStatus(
  agentId: string,
): Promise<WindowsServerADProfile> {
  const { data } = await axios.get(`/agents/${agentId}/ad-server/`);
  return data;
}

export async function runAgentADServerAction(
  agentId: string,
  action:
    | "test_secure_channel"
    | "repair_secure_channel"
    | "gpupdate_registerdns"
    | "sync_standalone_ntp"
    | "dcdiag_server_health"
    | "generate_deploy_info",
) {
  const { data } = await axios.post(`/agents/${agentId}/ad-server/`, {
    action,
  });
  return data;
}

export interface DiscoveredLANHost {
  ip_address: string;
  hostname: string;
  mac_address: string;
  discovery_source: string[];
  open_services: string[];
  estimated_type: string;
  smb_user: string;
  reachable: boolean;
  registered_in_rmm?: boolean;
  rmm_agent_id?: string;
  rmm_hostname?: string;
}

export interface UnitLANDiscoveryReport {
  server_hostname: string;
  server_platform: string;
  local_subnets: string[];
  total_found: number;
  computers_count: number;
  registered_count?: number;
  unregistered_count?: number;
  client_name?: string;
  site_name?: string;
  hosts: DiscoveredLANHost[];
  duration_ms: number;
  timestamp: string;
}

export async function runAgentLANDiscovery(
  agentId: string,
  subnet = "",
): Promise<UnitLANDiscoveryReport> {
  const { data } = await axios.post(`/agents/${agentId}/lan-discovery/`, {
    subnet,
  });
  return data;
}
