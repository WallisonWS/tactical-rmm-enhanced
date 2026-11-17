import asyncio

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from clients.serializers import SiteMinimumSerializer
from tacticalrmm.constants import AGENT_DEFER, PAAction
from tacticalrmm.helpers import notify_error
from tacticalrmm.permissions import _audit_log_filter, _has_perm_on_agent
from tacticalrmm.utils import get_default_timezone

from .models import AuditLog, DebugLog, PendingAction
from .permissions import AuditLogPerms, DebugLogPerms, PendingActionPerms
from .serializers import AuditLogSerializer, DebugLogSerializer, PendingActionSerializer


class GetAuditLogs(APIView):
    permission_classes = [IsAuthenticated, AuditLogPerms]

    def patch(self, request):
        from clients.models import Client

        pagination = request.data.get("pagination") or {}
        sort_by = pagination.get("sortBy") or "entry_time"
        descending = pagination.get("descending", True)
        order_by = f"-{sort_by}" if descending else f"{sort_by}"

        scopeFilter = Q()
        actionFilter = Q()
        objectFilter = Q()
        userFilter = Q()
        timeFilter = Q()
        searchFilter = Q()

        if "agentFilter" in request.data and request.data["agentFilter"]:
            scopeFilter = Q(agent_id__in=request.data["agentFilter"])

        elif "clientFilter" in request.data and request.data["clientFilter"]:
            clients = Client.objects.filter(pk__in=request.data["clientFilter"])
            agents = Agent.objects.filter(site__client__in=clients).values_list(
                "agent_id"
            )
            scopeFilter = Q(agent_id__in=agents)

        if "userFilter" in request.data and request.data["userFilter"]:
            userFilter = Q(username__in=request.data["userFilter"])

        if "actionFilter" in request.data and request.data["actionFilter"]:
            actionFilter = Q(action__in=request.data["actionFilter"])

        if "objectFilter" in request.data and request.data["objectFilter"]:
            objectFilter = Q(object_type__in=request.data["objectFilter"])

        if "timeFilter" in request.data and request.data["timeFilter"]:
            try:
                days = int(request.data["timeFilter"])
            except (TypeError, ValueError):
                days = 0
            if days > 0:
                now = djangotime.now()
                timeFilter = Q(
                    entry_time__lte=now,
                    entry_time__gte=now - djangotime.timedelta(days=days),
                )

        search_text = str(request.data.get("search") or "").strip()
        if search_text:
            searchFilter = (
                Q(username__icontains=search_text)
                | Q(agent__icontains=search_text)
                | Q(action__icontains=search_text)
                | Q(object_type__icontains=search_text)
                | Q(message__icontains=search_text)
            )

        audit_logs = (
            AuditLog.objects.filter(scopeFilter)
            .filter(userFilter)
            .filter(actionFilter)
            .filter(objectFilter)
            .filter(timeFilter)
            .filter(searchFilter)
            .filter(_audit_log_filter(request.user))
        ).order_by(order_by)

        rows_per_page = pagination.get("rowsPerPage") or 50
        page_num = pagination.get("page") or 1
        paginator = Paginator(audit_logs, rows_per_page)
        page_obj = paginator.get_page(page_num)

        # Preload site info in a single query to avoid N+1 lookups during serialization
        page_agent_ids = {item.agent_id for item in page_obj if item.agent_id}
        site_map = {}
        if page_agent_ids:
            for ag in Agent.objects.select_related("site__client").filter(
                agent_id__in=page_agent_ids
            ):
                if ag.site:
                    site_map[ag.agent_id] = SiteMinimumSerializer(ag.site).data

        ctx = {"default_tz": get_default_timezone(), "site_map": site_map}

        return Response(
            {
                "audit_logs": AuditLogSerializer(
                    page_obj, many=True, context=ctx
                ).data,
                "total": paginator.count,
            }
        )


class PendingActions(APIView):
    permission_classes = [IsAuthenticated, PendingActionPerms]

    def get(self, request, agent_id=None):
        if agent_id:
            agent = get_object_or_404(
                Agent.objects.defer(*AGENT_DEFER).prefetch_related("pendingactions"),
                agent_id=agent_id,
            )
            actions = (
                PendingAction.objects.filter(agent=agent)
                .select_related("agent__site", "agent__site__client")
                .defer("agent__services", "agent__wmi_detail")
            )
        else:
            actions = (
                PendingAction.objects.filter_by_role(request.user)  # type: ignore
                .select_related(
                    "agent__site",
                    "agent__site__client",
                )
                .defer("agent__services", "agent__wmi_detail")
            )

        return Response(PendingActionSerializer(actions, many=True).data)

    def delete(self, request, pk):
        action = get_object_or_404(PendingAction, pk=pk)

        if not _has_perm_on_agent(request.user, action.agent.agent_id):
            raise PermissionDenied()

        if action.action_type == PAAction.SCHED_REBOOT:
            nats_data = {
                "func": "delschedtask",
                "schedtaskpayload": {"name": action.details["taskname"]},
            }
            r = asyncio.run(action.agent.nats_cmd(nats_data, timeout=10))
            if r != "ok":
                return notify_error(r)

        action.delete()
        return Response(f"{action.agent.hostname}: {action.description} was cancelled")


class GetDebugLog(APIView):
    permission_classes = [IsAuthenticated, DebugLogPerms]

    def patch(self, request):
        agentFilter = Q()
        logTypeFilter = Q()
        logLevelFilter = Q()

        if "logTypeFilter" in request.data:
            logTypeFilter = Q(log_type=request.data["logTypeFilter"])

        if "logLevelFilter" in request.data:
            logLevelFilter = Q(log_level=request.data["logLevelFilter"])

        if "agentFilter" in request.data:
            agentFilter = Q(agent__agent_id=request.data["agentFilter"])

        debug_logs = (
            DebugLog.objects.prefetch_related("agent")
            .filter_by_role(request.user)  # type: ignore
            .filter(logLevelFilter)
            .filter(agentFilter)
            .filter(logTypeFilter)
        )

        ctx = {"default_tz": get_default_timezone()}
        ret = DebugLogSerializer(
            debug_logs.order_by("-entry_time")[0:1000], many=True, context=ctx
        ).data
        return Response(ret)
