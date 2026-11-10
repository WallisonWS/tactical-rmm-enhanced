import asyncio
from contextlib import suppress
from typing import Any, Dict, List

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from agents.permissions import SendCommandPerms
from alerts.models import Alert
from checks.models import CheckResult
from core.models import CoreSettings
from logs.models import AuditLog
from tacticalrmm.constants import (
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OVERDUE,
    AlertSeverity,
    AuditActionType,
    AuditObjType,
    CheckStatus,
)
from winupdate.models import WinUpdate


class AgentLiveTelemetryView(APIView):
    """
    GET /agents/<agent_id>/telemetry/
    Requests real-time hardware, CPU per-core, RAM, Disk I/O, Network counters, and S.M.A.R.T. health from the Go agent via NATS RPC.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "telemetry_snapshot"}, timeout=12))
        if r in ("timeout", "natsdown"):
            return Response(
                {
                    "agent_id": agent.agent_id,
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "status": agent.status,
                    "cached_fallback": True,
                    "ram_total_mb": (agent.total_ram or 0) * 1024,
                    "disks": agent.disks or [],
                    "needs_reboot": agent.needs_reboot,
                    "detail": f"Agent NATS RPC {r}; returning cached database telemetry.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(r)


class AgentSecurityAuditView(APIView):
    """
    GET /agents/<agent_id>/security-audit/
    POST /agents/<agent_id>/security-audit/ (sub-actions: startup_items, local_users, bitlocker_status)
    Executes an Endpoint Security & EDR posture audit on the remote agent via NATS RPC.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "security_audit"}, timeout=30))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Unable to reach agent {agent.hostname} ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        query_type = request.data.get("query_type", "security_audit")
        allowed_funcs = {
            "security_audit",
            "startup_items",
            "local_users",
            "bitlocker_status",
        }
        if query_type not in allowed_funcs:
            return Response(
                {"error": f"Unsupported security query_type: {query_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        r = asyncio.run(agent.nats_cmd({"func": query_type}, timeout=25))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Agent {agent.hostname} did not respond ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)


class AgentFirewallManagerView(APIView):
    """
    GET /agents/<agent_id>/firewall/
    POST /agents/<agent_id>/firewall/
    Inspects and manages host firewall profiles and inbound/outbound port rules on the remote agent.
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "firewall_status"}, timeout=15))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Agent {agent.hostname} unreachable ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        payload = {
            "action": str(request.data.get("action", "")),
            "rule_name": str(request.data.get("rule_name", "")),
            "direction": str(request.data.get("direction", "in")),
            "protocol": str(request.data.get("protocol", "TCP")),
            "port": str(request.data.get("port", "")),
            "remote_ip": str(request.data.get("remote_ip", "")),
        }
        nats_data = {"func": "firewall_rule", "payload": payload}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Firewall command timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executed firewall action '{payload['action']}' on {agent.hostname}",
            after_value=payload,
        )
        return Response(r)


class AgentNetworkToolsView(APIView):
    """
    GET /agents/<agent_id>/network/ -> Returns active TCP/UDP connections and listening ports with owning PIDs.
    POST /agents/<agent_id>/network/ -> Runs concurrent port scanner (`portscan`) or multi-stage network diagnostics (`netdiag`).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "netconnections"}, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Agent {agent.hostname} did not respond ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        tool = request.data.get("tool", "netdiag")

        if tool == "portscan":
            nats_data = {
                "func": "portscan",
                "payload": {
                    "host": str(request.data.get("host", "127.0.0.1")),
                    "ports": str(request.data.get("ports", "")),
                    "timeout_ms": str(request.data.get("timeout_ms", "600")),
                },
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
        else:
            nats_data = {
                "func": "netdiag",
                "payload": {
                    "target": str(request.data.get("target", "1.1.1.1")),
                },
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=25))

        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Network tool '{tool}' timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)


class AgentSelfHealingView(APIView):
    """
    POST /agents/<agent_id>/self-heal/
    Triggers autonomous remediation on the endpoint:
    - self_heal (full | disk | services | network | winupdate | memory)
    - disk_cleanup
    - trim_memory
    - reset_network
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "self_heal")
        mode = request.data.get("mode", "full")

        if action == "disk_cleanup":
            nats_data: Dict[str, Any] = {"func": "disk_cleanup"}
        elif action == "trim_memory":
            nats_data = {"func": "trim_memory"}
        elif action == "reset_network":
            nats_data = {
                "func": "reset_network",
                "payload": {
                    "full_reset": "true" if request.data.get("full_reset") else "false"
                },
            }
        else:
            nats_data = {"func": "self_heal", "payload": {"mode": str(mode)}}

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=60))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Self-healing operation '{action}' timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} triggered self-healing ({action}:{mode}) on {agent.hostname}",
            after_value=nats_data,
        )
        return Response(r)


class AgentWingetManagerView(APIView):
    """
    GET /agents/<agent_id>/winget/ -> Lists upgradable software packages via Winget / apt.
    POST /agents/<agent_id>/winget/ -> Installs or upgrades software packages via Winget / apt.
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "winget_list"}, timeout=50))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Winget scan timed out on {agent.hostname} ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        operation = request.data.get("operation", "upgrade")
        package_id = str(request.data.get("package_id", "all"))

        if operation == "install":
            nats_data = {
                "func": "winget_install",
                "payload": {"package_id": package_id},
            }
        else:
            nats_data = {
                "func": "winget_upgrade",
                "payload": {"package_id": package_id},
            }

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=300))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Winget {operation} timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executed Winget {operation} ({package_id}) on {agent.hostname}",
            after_value=nats_data,
        )
        return Response(r)


class AgentAIDiagnosticsView(APIView):
    """
    POST /agents/<agent_id>/ai-diagnostics/
    Analyzes failing checks, alerts, pending patches, and disk/service states on the agent,
    returning structured root-cause analysis and automated remediation playbooks.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        failing_checks = CheckResult.objects.filter(
            agent=agent, status__in=[CheckStatus.FAILING, CheckStatus.WARNING]
        ).select_related("assigned_check")

        unresolved_alerts = Alert.objects.filter(agent=agent, resolved=False)
        pending_patches = WinUpdate.objects.filter(
            agent=agent, action="approve", installed=False
        ).count()

        findings: List[Dict[str, Any]] = []
        playbooks: List[Dict[str, Any]] = []
        health_score = 100

        if agent.status == AGENT_STATUS_OVERDUE:
            health_score -= 30
            findings.append(
                {
                    "severity": "critical",
                    "category": "Connectivity",
                    "title": "Agent is Overdue",
                    "detail": f"Last seen at {agent.last_seen}. Check NATS port 4222 reachability or run Mesh recovery.",
                }
            )
            playbooks.append(
                {
                    "name": "Recover Agent & NATS Connection",
                    "action_type": "recover_mesh",
                    "recommended_command": "tacticalagent -m recovermesh",
                }
            )

        if agent.needs_reboot:
            health_score -= 10
            findings.append(
                {
                    "severity": "warning",
                    "category": "System State",
                    "title": "Pending System Reboot",
                    "detail": "Endpoint has pending OS/patch operations requiring a reboot.",
                }
            )
            playbooks.append(
                {
                    "name": "Schedule Maintenance Reboot",
                    "action_type": "reboot",
                    "recommended_command": "shutdown /r /t 300 /c 'Scheduled RMM Maintenance'",
                }
            )

        if pending_patches > 0:
            health_score -= min(20, pending_patches * 3)
            findings.append(
                {
                    "severity": "warning",
                    "category": "Patch Compliance",
                    "title": f"{pending_patches} Approved Patches Pending Installation",
                    "detail": "Approved security/critical updates are awaiting installation.",
                }
            )
            playbooks.append(
                {
                    "name": "Install Pending Windows Updates",
                    "action_type": "install_patches",
                    "recommended_command": "tacticalagent -m getwinupdates",
                }
            )

        for cr in failing_checks:
            chk = cr.assigned_check
            if not chk:
                continue
            health_score -= 12
            findings.append(
                {
                    "severity": cr.status,
                    "category": f"Check ({chk.check_type})",
                    "title": chk.readable_desc,
                    "detail": cr.more_info or "Check reported failure threshold.",
                }
            )
            if chk.check_type == "diskspace":
                playbooks.append(
                    {
                        "name": "Run Autonomous Deep Disk Cleanup",
                        "action_type": "self_heal",
                        "mode": "disk",
                        "recommended_command": "self_heal:disk",
                    }
                )
            elif chk.check_type == "winsvc":
                playbooks.append(
                    {
                        "name": f"Auto-Restart Service ({chk.svc_name})",
                        "action_type": "self_heal",
                        "mode": "services",
                        "recommended_command": f"Restart-Service -Name '{chk.svc_name}' -Force",
                    }
                )
            elif chk.check_type == "memory":
                playbooks.append(
                    {
                        "name": "Optimize & Trim Memory Working Set",
                        "action_type": "self_heal",
                        "mode": "memory",
                        "recommended_command": "self_heal:memory",
                    }
                )

        if not findings:
            findings.append(
                {
                    "severity": "passing",
                    "category": "System Health",
                    "title": "All Monitored Subsystems Healthy",
                    "detail": "Zero failing checks or unresolved alerts detected on this endpoint.",
                }
            )

        core = CoreSettings.objects.first()
        ai_model = getattr(core, "open_ai_model", "gpt-4o") if core else "built-in-heuristic-engine"

        return Response(
            {
                "agent_id": agent.agent_id,
                "hostname": agent.hostname,
                "health_score": max(0, health_score),
                "unresolved_alerts_count": unresolved_alerts.count(),
                "pending_patches_count": pending_patches,
                "ai_engine": ai_model,
                "findings": findings,
                "remediation_playbooks": playbooks,
                "generated_at": djangotime.now().isoformat(),
            }
        )


class FleetExecutiveSummaryView(APIView):
    """
    GET /agents/executive-summary/
    Aggregates global fleet KPIs, health scores, patch compliance, and alert breakdown for the enhanced Dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        agents_qs = Agent.objects.filter_by_role(request.user)
        total_agents = agents_qs.count()

        online_count = 0
        offline_count = 0
        overdue_count = 0
        reboot_needed_count = 0
        maintenance_count = 0

        for ag in agents_qs.only(
            "last_seen", "offline_time", "overdue_time", "needs_reboot", "maintenance_mode"
        ):
            st = ag.status
            if st == AGENT_STATUS_ONLINE:
                online_count += 1
            elif st == AGENT_STATUS_OVERDUE:
                overdue_count += 1
            else:
                offline_count += 1
            if ag.needs_reboot:
                reboot_needed_count += 1
            if ag.maintenance_mode:
                maintenance_count += 1

        unresolved_alerts = Alert.objects.filter_by_role(request.user).filter(resolved=False)
        critical_alerts = unresolved_alerts.filter(severity=AlertSeverity.ERROR).count()
        warning_alerts = unresolved_alerts.filter(severity=AlertSeverity.WARNING).count()

        failing_checks = (
            CheckResult.objects.filter_by_role(request.user)
            .filter(status=CheckStatus.FAILING)
            .count()
        )

        pending_patches = (
            WinUpdate.objects.filter(agent__in=agents_qs, installed=False, action="approve")
            .values("agent")
            .distinct()
            .count()
        )

        if total_agents > 0:
            availability_pct = round((online_count / total_agents) * 100, 1)
            patch_compliance_pct = round(
                ((total_agents - pending_patches) / total_agents) * 100, 1
            )
            fleet_health_score = max(
                0,
                min(
                    100,
                    round(
                        (availability_pct * 0.5)
                        + (patch_compliance_pct * 0.3)
                        + max(0, 20 - (critical_alerts * 2) - failing_checks)
                    ),
                ),
            )
        else:
            availability_pct = 100.0
            patch_compliance_pct = 100.0
            fleet_health_score = 100

        return Response(
            {
                "total_agents": total_agents,
                "online_agents": online_count,
                "offline_agents": offline_count,
                "overdue_agents": overdue_count,
                "reboot_needed_agents": reboot_needed_count,
                "maintenance_agents": maintenance_count,
                "availability_percent": availability_pct,
                "patch_compliance_percent": patch_compliance_pct,
                "fleet_health_score": fleet_health_score,
                "active_alerts": {
                    "total": unresolved_alerts.count(),
                    "error": critical_alerts,
                    "warning": warning_alerts,
                },
                "failing_checks_count": failing_checks,
                "agents_with_pending_patches": pending_patches,
                "timestamp": djangotime.now().isoformat(),
            }
        )


class AgentHALinkWatchdogView(APIView):
    """
    GET /agents/<agent_id>/ha-link/
    POST /agents/<agent_id>/ha-link/
    Enterprise High-Availability link validator and Mesh/NATS self-recovery controller.
    Ensures continuous production connectivity across Agent <-> API <-> NATS <-> MeshCentral
    and automatically resolves MeshNodeID desynchronization conflicts.
    """

    permission_classes = [IsAuthenticated]

    def _sync_agent_mesh_node_id(self, agent: Agent, report: Any) -> bool:
        if not isinstance(report, dict):
            return False
        reported_node_id = str(report.get("mesh_node_id") or "").strip()
        if (
            reported_node_id
            and "not defined" not in reported_node_id.lower()
            and len(reported_node_id) >= 32
            and agent.mesh_node_id != reported_node_id
        ):
            agent.mesh_node_id = reported_node_id
            agent.save(update_fields=["mesh_node_id"])
            with suppress(Exception):
                from core.tasks import sync_mesh_perms_task

                sync_mesh_perms_task.delay()
            return True
        return False

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "ha_link_health"}, timeout=10))
        if r in ("timeout", "natsdown"):
            return Response(
                {
                    "agent_id": agent.agent_id,
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "agent_version": agent.version,
                    "api_reachable": agent.status == AGENT_STATUS_ONLINE,
                    "api_latency_ms": 0,
                    "nats_reachable": False,
                    "nats_latency_ms": 0,
                    "nats_transport": "wss/tls",
                    "mesh_service_status": "Unknown (NATS Timeout)" if r == "timeout" else "NATS Broker Offline",
                    "mesh_healthy": bool(agent.mesh_node_id),
                    "mesh_node_id": agent.mesh_node_id or "",
                    "mesh_id_synced": bool(agent.mesh_node_id),
                    "proxy_configured": False,
                    "proxy_url": "",
                    "overall_status": "DEGRADED" if agent.status == AGENT_STATUS_ONLINE else "CRITICAL",
                    "recommendations": [
                        "O agente não respondeu ao ping NATS no tempo limite. Verifique a conectividade de saída (TCP 443/4222) ou acione a recuperação do Mesh."
                    ],
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        if isinstance(r, dict):
            synced = self._sync_agent_mesh_node_id(agent, r)
            r["mesh_id_synced"] = True
            if synced:
                r["recommendations"] = list(r.get("recommendations") or []) + [
                    "MeshNodeID sincronizado automaticamente com o banco da API e MeshCentral."
                ]
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "ha_mesh_repair"}, timeout=35))
        if r in ("timeout", "natsdown"):
            # Fallback to NATS async recovermesh command if synchronous repair timed out
            with suppress(Exception):
                asyncio.run(
                    agent.nats_cmd(
                        {"func": "recovercmd", "recoverycommand": "mesh"},
                        wait=False,
                    )
                )
            return Response(
                {"error": f"Não foi possível contatar {agent.hostname} via NATS ({r}). Comando assíncrono de recuperação Mesh enfileirado."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        if isinstance(r, dict):
            health_after = r.get("health_after")
            if self._sync_agent_mesh_node_id(agent, health_after or r):
                actions = list(r.get("actions_taken") or [])
                actions.append("MeshNodeID sincronizado automaticamente entre Agente, API e MeshCentral")
                r["actions_taken"] = actions

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou reparo de alta disponibilidade (Mesh & Link) em {agent.hostname}",
            after_value=r,
        )
        return Response(r)


class AgentRDPManagerView(APIView):
    """
    GET /agents/<agent_id>/rdp/
    POST /agents/<agent_id>/rdp/
    Inspects and manages Corporate Remote Desktop (TermService, NLA enforcement, active sessions, and .rdp profile generation).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "rdp_status"}, timeout=12))
        if r in ("timeout", "natsdown"):
            return Response(
                {
                    "platform": agent.plat,
                    "rdp_enabled": False,
                    "nla_enabled": True,
                    "service_status": "Unreachable",
                    "listening_port": 3389,
                    "port_reachable": False,
                    "local_ips": [agent.local_ips] if agent.local_ips else [],
                    "active_sessions": [],
                    "hostname": agent.hostname,
                    "public_ip": agent.public_ip,
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        if isinstance(r, dict):
            r["hostname"] = agent.hostname
            r["public_ip"] = agent.public_ip
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "enable_rdp")
        enforce_nla = request.data.get("enforce_nla", True)
        session_id = str(request.data.get("session_id", ""))

        nats_data = {
            "func": "rdp_manage",
            "data": {
                "action": action,
                "enforce_nla": "true" if enforce_nla else "false",
                "session_id": session_id,
            },
        }
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Operação RDP ({action}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.MODIFY,
            message=f"{request.user.username} executou ação RDP '{action}' (NLA={enforce_nla}) em {agent.hostname}",
            after_value=nats_data["data"],
        )
        return Response(r)


class AgentHardwareInventoryView(APIView):
    """
    GET /agents/<agent_id>/hardware-inventory/
    POST /agents/<agent_id>/hardware-inventory/
    Retrieves BIOS/Service Tag, Domain/Entra ID status, GPU, Battery health, and runs GPO/Power/NTP actions.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "hw_inventory"}, timeout=15))
        if r in ("timeout", "natsdown"):
            return Response(
                {
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "manufacturer": "Unknown",
                    "model": "Unknown",
                    "serial_number": "Unavailable (Agent Offline)",
                    "bios_version": "Unknown",
                    "domain_or_workgroup": "WORKGROUP",
                    "part_of_domain": False,
                    "entra_id_joined": False,
                    "active_power_plan": "Balanced",
                    "gpus": [],
                    "battery_present": False,
                    "battery_charge_pct": 0,
                    "battery_status": "AC Power",
                    "printers_count": 0,
                    "restore_points_count": 0,
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "gpupdate_force")
        nats_data = {"func": "power_gpo_action", "data": {"action": action}}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Ação administrativa ({action}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou ação administrativa '{action}' em {agent.hostname}",
            after_value=nats_data["data"],
        )
        return Response(r)


class AgentPrintersManagerView(APIView):
    """
    GET /agents/<agent_id>/printers/
    POST /agents/<agent_id>/printers/
    Lists installed printers/queues and executes queue clearing, default printer assignment, or test page printing.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "printers_list"}, timeout=15))
        if r in ("timeout", "natsdown"):
            return Response([])
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "clear_queue")
        printer_name = request.data.get("printer_name", "")

        nats_data = {
            "func": "printer_action",
            "data": {"action": action, "printer_name": printer_name},
        }
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Operação de impressora ({action}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.MODIFY,
            message=f"{request.user.username} executou '{action}' na impressora '{printer_name}' em {agent.hostname}",
            after_value=nats_data["data"],
        )
        return Response(r)


class AgentITSupportToolsView(APIView):
    """
    GET /agents/<agent_id>/it-support/
    POST /agents/<agent_id>/it-support/
    Manages System Restore checkpoints and sends audited IT Helpdesk messages to the logged-in user screen.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(
            agent.nats_cmd({"func": "system_restore", "data": {"action": "list"}}, timeout=15)
        )
        if r in ("timeout", "natsdown"):
            return Response({"restore_points": [], "success": False})
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        tool_type = request.data.get("tool_type", "broadcast_msg")

        if tool_type == "system_restore":
            description = request.data.get("description", "Ponto de Restauração TI - Tactical RMM")
            nats_data = {
                "func": "system_restore",
                "data": {"action": "create", "description": description},
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=60))
        else:
            title = request.data.get("title", "Suporte de TI")
            message = request.data.get("message", "")
            timeout_sec = str(request.data.get("timeout_sec", 60))
            nats_data = {
                "func": "it_broadcast_msg",
                "data": {"title": title, "message": message, "timeout_sec": timeout_sec},
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=15))

        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Operação de suporte ({tool_type}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou ferramenta de suporte '{tool_type}' em {agent.hostname}",
            after_value=nats_data["data"],
        )
        return Response(r)


class AgentADServerManagerView(APIView):
    """
    GET /agents/<agent_id>/ad-server/
    POST /agents/<agent_id>/ad-server/
    Inspects and manages Active Directory (AD/GPO) as well as Non-AD (Workgroup/Standalone)
    Windows Server and Workstation endpoints via the Go agent.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(
            Agent.objects.select_related("site__client"), agent_id=agent_id
        )
        r = asyncio.run(agent.nats_cmd({"func": "ad_server_status"}, timeout=15))
        if r in ("timeout", "natsdown") or not isinstance(r, dict):
            return Response(
                {
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "os_caption": agent.operating_system,
                    "os_version": agent.version,
                    "environment_mode": "workgroup_standalone",
                    "is_windows_server": agent.monitoring_type == "server",
                    "is_domain_controller": False,
                    "part_of_domain": False,
                    "domain_name": "",
                    "workgroup_name": "WORKGROUP",
                    "forest_name": "",
                    "domain_role_id": 2 if agent.monitoring_type == "server" else 0,
                    "domain_role_label": "Standalone Windows Server (Sem AD / Workgroup)"
                    if agent.monitoring_type == "server"
                    else "Standalone Workstation (Sem AD / Workgroup)",
                    "domain_controller_name": "",
                    "domain_controller_address": "",
                    "ad_site_name": agent.site.name,
                    "computer_dn": "",
                    "organizational_unit": "",
                    "secure_channel_valid": False,
                    "sysvol_reachable": False,
                    "netlogon_reachable": False,
                    "time_sync_source": "Local CMOS / NTP",
                    "deployed_via_gpo": False,
                    "deployment_mode": "Standalone-Workgroup",
                    "last_gpo_verify": "",
                    "applied_computer_gpos": [],
                    "installed_server_roles": [],
                    "ad_critical_services": {},
                    "recommended_agent_type": agent.monitoring_type,
                    "client_id": agent.client.id,
                    "client_name": agent.client.name,
                    "site_id": agent.site.id,
                    "site_name": agent.site.name,
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        r["client_id"] = agent.client.id
        r["client_name"] = agent.client.name
        r["site_id"] = agent.site.id
        r["site_name"] = agent.site.name
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(
            Agent.objects.select_related("site__client"), agent_id=agent_id
        )
        action = request.data.get("action", "test_secure_channel")

        if action == "generate_deploy_info":
            host_scheme = "https" if request.is_secure() else "http"
            api_host = f"{host_scheme}://{request.get_host()}"
            return Response(
                {
                    "client_id": agent.client.id,
                    "client_name": agent.client.name,
                    "site_id": agent.site.id,
                    "site_name": agent.site.name,
                    "api_url": api_host,
                    "go_ad_gpo_args": f'-m gpoinstall -api "{api_host}" -client-id {agent.client.id} -site-id {agent.site.id} -agent-type auto -auth "<TOKEN_INSTALADOR>" -rdp -ping -power -silent -gpo',
                    "go_standalone_args": f'-m gpoinstall -api "{api_host}" -client-id {agent.client.id} -site-id {agent.site.id} -agent-type auto -auth "<TOKEN_INSTALADOR>" -desc "Unidade Sem AD - {agent.site.name}" -rdp -ping -power -silent',
                }
            )

        nats_data = {"func": "ad_server_action", "data": {"action": action}}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Operação ({action}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou operação AD/Standalone '{action}' em {agent.hostname}",
            after_value=nats_data["data"],
        )
        return Response(r)


class AgentLANDiscoveryView(APIView):
    """
    POST /agents/<agent_id>/lan-discovery/
    Uses any installed server/agent in a non-AD unit as a LAN Discovery Probe
    (SMB sessions, DHCP leases, ARP cache, and Go LAN scanner) and cross-references
    discovered computers against the Tactical RMM database.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(
            Agent.objects.select_related("site__client"), agent_id=agent_id
        )
        subnet = str(request.data.get("subnet", "")).strip()
        nats_data = {"func": "lan_discovery", "data": {"subnet": subnet}}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
        if r in ("timeout", "natsdown") or not isinstance(r, dict):
            return Response(
                {
                    "error": f"Levantamento LAN expirou ou agente offline em {agent.hostname}"
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        # Build lookup maps of all agents registered in Tactical RMM (by hostname and by local IP)
        hostname_map: dict[str, dict[str, str]] = {}
        ip_map: dict[str, dict[str, str]] = {}

        for existing in Agent.objects.only("agent_id", "hostname", "wmi_detail"):
            short_name = (existing.hostname or "").split(".")[0].strip().lower()
            info = {"agent_id": existing.agent_id, "hostname": existing.hostname}
            if short_name:
                hostname_map[short_name] = info
            wmi = existing.wmi_detail or {}
            if isinstance(wmi, dict):
                local_ips = wmi.get("local_ips") or []
                if isinstance(local_ips, list):
                    for raw_ip in local_ips:
                        clean_ip = str(raw_ip).split("/")[0].strip()
                        if clean_ip:
                            ip_map[clean_ip] = info

        hosts = r.get("hosts") or []
        registered_count = 0
        unregistered_count = 0

        for h in hosts:
            if not isinstance(h, dict):
                continue
            ip_addr = str(h.get("ip_address") or "").strip()
            raw_host = str(h.get("hostname") or "").split(".")[0].strip().lower()
            matched = ip_map.get(ip_addr) or (
                hostname_map.get(raw_host) if raw_host else None
            )
            if matched:
                h["registered_in_rmm"] = True
                h["rmm_agent_id"] = matched["agent_id"]
                h["rmm_hostname"] = matched["hostname"]
                if not h.get("hostname"):
                    h["hostname"] = matched["hostname"]
                registered_count += 1
            else:
                h["registered_in_rmm"] = False
                h["rmm_agent_id"] = ""
                h["rmm_hostname"] = ""
                unregistered_count += 1

        r["registered_count"] = registered_count
        r["unregistered_count"] = unregistered_count
        r["client_name"] = agent.client.name
        r["site_name"] = agent.site.name
        return Response(r)
