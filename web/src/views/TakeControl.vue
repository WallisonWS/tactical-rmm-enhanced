<template>
  <div>
    <q-bar>
      <span class="text-caption">
        TRMM Agent Status:
        <q-badge :color="statusColor" :label="status" />
      </span>
      <q-space />
      <q-btn
        class="q-mr-md"
        color="indigo-6"
        size="sm"
        label="Conectar RDP (.rdp)"
        icon="desktop_windows"
        :loading="rdpConnecting"
        @click="connectNativeRDP"
      />
      <q-btn
        class="q-mr-md"
        color="primary"
        size="sm"
        label="Restart Connection"
        icon="refresh"
        @click="restartMeshService"
      />
      <q-checkbox
        v-if="isWorkstation"
        v-model="autoPauseOnExit"
        dense
        dark
        color="teal-4"
        class="q-mr-md text-caption"
        label="Auto-pausar Mesh ao sair"
      >
        <q-tooltip>
          Ao fechar esta janela de controle remoto, pausa o Mesh Agent automaticamente na estação para não bloquear sites de bancos (Warsaw / Topaz)
        </q-tooltip>
      </q-checkbox>
      <q-btn
        class="q-mr-md"
        color="teal-7"
        size="sm"
        label="Modo Banco (Pausar Mesh)"
        icon="account_balance"
        @click="pauseMeshForBanking"
      >
        <q-tooltip>
          Coloca o Mesh Agent em repouso (Sob Demanda) para que o funcionário use sites de bancos sem bloqueio, mantendo o monitoramento Tactical RMM 100% Online
        </q-tooltip>
      </q-btn>
      <q-btn
        :color="dash_negative_color"
        size="sm"
        label="Recover Connection"
        icon="fas fa-first-aid"
        @click="repairMeshCentral"
      />
      <q-space />
    </q-bar>
    <div class="q-video" :style="{ height: `${$q.screen.height - 26}px` }">
      <iframe
        v-show="control"
        :src="control"
        allow="clipboard-read; clipboard-write"
        allowfullscreen
        frameborder="0"
      ></iframe>
    </div>
  </div>
</template>

<script>
// composition imports
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useStore } from "vuex";
import { useRoute } from "vue-router";
import { useMeta, useQuasar } from "quasar";
import { fetchAgentMeshCentralURLs, sendAgentRecoverMesh, fetchAgent } from "@/api/agents";
import { fetchDashboardInfo } from "@/api/core";
import { sendAgentServiceAction } from "@/api/services";
import { manageAgentRDP, downloadNativeRDPFile, pauseAgentMeshForBanking } from "@/api/enhanced";
import { syncDarkModeWithSavedPalette } from "@/utils/themePalettes";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
  name: "TakeControl",
  setup() {
    const isWorkstation = ref(false);
    const autoPauseOnExit = ref(true);

    function handlePageHide() {
      if (isWorkstation.value && autoPauseOnExit.value) {
        pauseAgentMeshForBanking(String(params.agent_id), true).catch(() => {});
      }
    }

    // vue lifecycle hooks
    onMounted(() => {
      dashInfo();
      getDashInfo();
      getMeshURLs();
      if (typeof window !== "undefined") {
        window.addEventListener("pagehide", handlePageHide);
      }
    });

    onBeforeUnmount(() => {
      if (typeof window !== "undefined") {
        window.removeEventListener("pagehide", handlePageHide);
      }
      handlePageHide();
    });

    // quasar setup
    const $q = useQuasar();
    const store = useStore();
    const dash_positive_color = computed(() => store.state.dash_positive_color);
    const dash_negative_color = computed(() => store.state.dash_negative_color);
    const dash_warning_color = computed(() => store.state.dash_warning_color);

    // vue router
    const { params } = useRoute();

    // take control setup
    const control = ref("");
    const status = ref(null);
    const agentHostname = ref("");
    const rdpConnecting = ref(false);

    const statusColor = computed(() => {
      switch (status.value) {
        case "online":
          return dash_positive_color.value;
        case "offline":
          return dash_warning_color.value;
        default:
          return dash_negative_color.value;
      }
    });

    // TODO refactor this so we're not calling the api twice
    const dashInfo = () => {
      store.dispatch("getDashInfo", false);
    };

    async function getMeshURLs() {
      $q.loading.show();
      try {
        const data = await fetchAgentMeshCentralURLs(params.agent_id);
        control.value = data.control;
        status.value = data.status;
        isWorkstation.value = data.monitoring_type === "workstation" && data.plat === "windows";
        agentHostname.value = data.hostname || "";
        useMeta({
          title: `${data.hostname} - ${data.client} - ${data.site} | Take Control`,
        });
      } catch (e) {
        console.error(e);
      }
      $q.loading.hide();
    }

    async function getDashInfo() {
      const { dark_mode, loading_bar_color } = await fetchDashboardInfo();
      syncDarkModeWithSavedPalette(dark_mode);
      $q.loadingBar.setDefaults({ color: loading_bar_color });
    }

    async function repairMeshCentral() {
      control.value = "";
      $q.loading.show({ message: "Attempting to repair Mesh Agent" });
      try {
        const data = await sendAgentRecoverMesh(params.agent_id);
        await getMeshURLs();
        setTimeout(() => {
          notifySuccess(data);
        }, 500);
      } catch (e) {
        console.error(e);
      }
      $q.loading.hide();
    }

    async function restartMeshService() {
      $q.loading.show({ message: "Restarting Mesh Agent" });
      const data = {
        sv_action: "restart",
      };

      try {
        await sendAgentServiceAction(params.agent_id, "mesh agent", data);
        control.value = "";
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await getMeshURLs();
        notifySuccess("Mesh agent service was restarted");
      } catch (e) {
        console.error(e);
      }

      $q.loading.hide();
    }

    async function connectNativeRDP() {
      rdpConnecting.value = true;
      try {
        await manageAgentRDP(params.agent_id, { action: "enable" });
      } catch (e) {
        // Proceed to download RDP file even if agent NATS call times out
      }
      try {
        const agentData = await fetchAgent(params.agent_id);
        const rawIps = String(agentData?.local_ips || agentData?.local_ip || "");
        const firstIp =
          rawIps
            .split(",")
            .map((s) => s.trim())
            .find((ip) => ip && !ip.startsWith("127.")) ||
          agentData?.hostname ||
          agentHostname.value;
        const hostLabel = agentData?.hostname || agentHostname.value || "workstation";
        downloadNativeRDPFile(hostLabel, firstIp, 3389);
        notifySuccess(`Conexão RDP (${firstIp}) habilitada e arquivo ${hostLabel}.rdp baixado!`);
      } catch (e) {
        if (agentHostname.value) {
          downloadNativeRDPFile(agentHostname.value, agentHostname.value, 3389);
        } else {
          notifyError("Não foi possível obter o IP do computador para conexão RDP.");
        }
      } finally {
        rdpConnecting.value = false;
      }
    }

    async function pauseMeshForBanking() {
      $q.loading.show({ message: "Ativando Modo Compatibilidade Bancária (Mesh Sob Demanda)..." });
      try {
        const msg = await pauseAgentMeshForBanking(String(params.agent_id), false);
        notifySuccess(
          msg ||
            "Modo Compatibilidade Bancária ativado! O funcionário já pode acessar os bancos normalmente e o monitoramento Tactical continua Online.",
        );
      } catch (e) {
        notifyError("Falha ao ativar Modo Compatibilidade Bancária.");
      } finally {
        $q.loading.hide();
      }
    }

    return {
      // reactive data
      control,
      status,
      statusColor,
      dash_negative_color,
      rdpConnecting,
      isWorkstation,
      autoPauseOnExit,

      // methods
      repairMeshCentral,
      restartMeshService,
      connectNativeRDP,
      pauseMeshForBanking,
    };
  },
};
</script>
