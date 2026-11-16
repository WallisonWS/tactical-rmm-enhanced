import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { useDashWSConnection } from "@/websocket/websocket";

export interface WSAgentCount {
  total_server_count: number;
  total_server_offline_count: number;
  total_workstation_count: number;
  total_workstation_offline_count: number;
  days_until_cert_expires: number;
}

export const useDashboardStore = defineStore("dashboard", () => {
  // updated by dashboard.agentcount WS event and HTTP /core/dashinfo/
  const serverCount = ref(0);
  const serverOfflineCount = ref(0);
  const workstationCount = ref(0);
  const workstationOfflineCount = ref(0);
  const daysUntilCertExpires = ref(180);
  const summaryVersion = ref(0);

  const { data } = useDashWSConnection();

  function setAgentCounts(incomingData: Partial<WSAgentCount>) {
    if (typeof incomingData.total_server_count === "number") {
      serverCount.value = incomingData.total_server_count;
    }
    if (typeof incomingData.total_server_offline_count === "number") {
      serverOfflineCount.value = incomingData.total_server_offline_count;
    }
    if (typeof incomingData.total_workstation_count === "number") {
      workstationCount.value = incomingData.total_workstation_count;
    }
    if (typeof incomingData.total_workstation_offline_count === "number") {
      workstationOfflineCount.value = incomingData.total_workstation_offline_count;
    }
    if (typeof incomingData.days_until_cert_expires === "number") {
      daysUntilCertExpires.value = incomingData.days_until_cert_expires;
    }
  }

  function triggerSummaryRefresh() {
    summaryVersion.value += 1;
  }

  // watch for data ws data
  watch(data, (newValue) => {
    if (newValue.action === "dashboard.agentcount") {
      setAgentCounts(newValue.data as WSAgentCount);
    }
  });

  return {
    serverCount,
    serverOfflineCount,
    workstationCount,
    workstationOfflineCount,
    daysUntilCertExpires,
    summaryVersion,
    setAgentCounts,
    triggerSummaryRefresh,
  };
});
