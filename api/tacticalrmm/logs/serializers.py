from rest_framework import serializers

from .models import AuditLog, DebugLog, PendingAction


class AuditLogSerializer(serializers.ModelSerializer):
    entry_time = serializers.ReadOnlyField()
    ip_address = serializers.ReadOnlyField(source="debug_info.ip")
    site = serializers.SerializerMethodField()

    def get_site(self, obj):
        site_map = self.context.get("site_map")
        if site_map is not None:
            return site_map.get(obj.agent_id)

        from agents.models import Agent
        from clients.serializers import SiteMinimumSerializer

        if obj.agent_id:
            agent = (
                Agent.objects.select_related("site__client")
                .filter(agent_id=obj.agent_id)
                .first()
            )
            if agent and agent.site:
                return SiteMinimumSerializer(agent.site).data

        return None

    class Meta:
        model = AuditLog
        fields = "__all__"


class PendingActionSerializer(serializers.ModelSerializer):
    hostname = serializers.ReadOnlyField(source="agent.hostname")
    client = serializers.ReadOnlyField(source="agent.client.name")
    site = serializers.ReadOnlyField(source="agent.site.name")
    due = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()

    class Meta:
        model = PendingAction
        fields = "__all__"


class DebugLogSerializer(serializers.ModelSerializer):
    agent = serializers.ReadOnlyField(source="agent.hostname")
    entry_time = serializers.ReadOnlyField()

    class Meta:
        model = DebugLog
        fields = "__all__"
