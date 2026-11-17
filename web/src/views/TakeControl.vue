<template>
  <div>
    <q-bar>
      <span class="text-caption q-mr-sm">
        Status do Agente TRMM:
        <q-badge :color="statusColor" :label="status || '...'" />
      </span>
      <q-badge
        v-if="natsOnline !== null"
        :color="natsOnline ? 'positive' : 'negative'"
        class="q-mr-xs text-caption"
        :label="natsOnline ? 'NATS: Online' : 'NATS: Inacessível'"
      />
      <q-badge
        v-if="meshConnected !== null"
        :color="meshConnected ? 'teal-7' : 'warning'"
        class="q-mr-sm text-caption"
        :label="meshConnected ? 'Mesh: Conectado' : 'Mesh: Desconectado'"
      />
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
        <q-tooltip max-width="340px">
          <b>Modo Banco automático ao encerrar:</b><br />
          Quando você fechar esta tela, o serviço <b>Mesh Agent</b> volta para repouso (Sob Demanda) para não ativar bloqueios de bancos (Warsaw / Topaz / GBPlugin). O agente <b>Tactical RMM permanece 100% online</b> e religa o Mesh automaticamente no próximo acesso remoto.
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
        <q-tooltip max-width="340px">
          <b>O que este botão faz agora:</b><br />
          Pausa somente o serviço de tela remota <b>Mesh Agent</b> (modo Manual / Sob Demanda) para liberar imediatamente o acesso a sites bancários (Warsaw / Topaz) sem desligar o monitoramento, alertas ou scripts do <b>Tactical RMM</b>.
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
    <div class="q-video relative-position" :style="{ height: `${$q.screen.height - 26}px` }">
      <iframe
        v-if="control && (meshConnected !== false || forceShowIframe)"
        :key="iframeKey"
        :src="control"
        allow="clipboard-read; clipboard-write"
        allowfullscreen
        frameborder="0"
      ></iframe>
      <div
        v-else-if="!loadingConn"
        class="column flex-center fit q-pa-lg text-center"
        style="background: #111827; color: #f8fafc"
      >
        <q-icon
          :name="natsOnline ? 'sync_problem' : 'cloud_off'"
          size="56px"
          :color="natsOnline ? 'warning' : 'negative'"
          class="q-mb-md"
        />
        <div class="text-h6 q-mb-sm">
          {{
            natsOnline
              ? "Agente Tactical Online — Mesh Agent ainda não conectado"
              : "Computador inacessível via NATS neste momento"
          }}
        </div>
        <div class="text-body2 text-grey-4 q-mb-md" style="max-width: 620px; line-height: 1.5">
          {{
            diagnosticReason ||
            "Não foi possível estabelecer a sessão MeshCentral automaticamente para este computador."
          }}
        </div>
        <div v-if="meshServiceStatus && meshServiceStatus !== 'Unknown'" class="text-caption text-grey-5 q-mb-md">
          Serviço Mesh no endpoint: <b>{{ meshServiceStatus }}</b>
        </div>
        <div class="row q-gutter-sm justify-center">
          <q-btn
            color="primary"
            icon="refresh"
            label="Testar e Reconectar"
            no-caps
            @click="getMeshURLs"
          />
          <q-btn
            color="negative"
            icon="fas fa-first-aid"
            label="Recuperar / Reinstalar Mesh"
            no-caps
            @click="repairMeshCentral"
          />
          <q-btn
            v-if="agentPlat === 'windows'"
            color="indigo-6"
            icon="desktop_windows"
            label="Conectar RDP (.rdp)"
            no-caps
            :loading="rdpConnecting"
            @click="connectNativeRDP"
          />
          <q-btn
            v-if="control"
            flat
            color="grey-4"
            label="Abrir Iframe Mesh assim mesmo"
            no-caps
            @click="forceShowIframe = true"
          />
        </div>
      </div>
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
import {
  manageAgentRDP,
  downloadNativeRDPFile,
  pauseAgentMeshForBanking,
  resolveFirstReachableHost,
} from "@/api/enhanced";
import { syncDarkModeWithSavedPalette } from "@/utils/themePalettes";
import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";

export default {
  name: "TakeControl",
  setup() {
    const isWorkstation = ref(false);
    const autoPauseOnExit = ref(true);
    let didPauseOnExit = false;

    function handlePageHide() {
      if (didPauseOnExit) return;
      if (isWorkstation.value && autoPauseOnExit.value) {
        didPauseOnExit = true;
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
    const agentPlat = ref("windows");
    const rdpConnecting = ref(false);
    const natsOnline = ref(null);
    const meshConnected = ref(null);
    const meshServiceStatus = ref("");
    const diagnosticReason = ref("");
    const loadingConn = ref(true);
    const forceShowIframe = ref(false);
    const iframeKey = ref(0);
    let autoRepairTried = false;

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
      didPauseOnExit = false;
      loadingConn.value = true;
      forceShowIframe.value = false;
      $q.loading.show({ message: "Verificando NATS e conectando ao Mesh Agent..." });
      try {
        const data = await fetchAgentMeshCentralURLs(params.agent_id);
        if (!data) {
          diagnosticReason.value = "Falha ao consultar o servidor Tactical RMM / MeshCentral.";
          meshConnected.value = false;
          return;
        }
        control.value = data.control;
        status.value = data.status;
        isWorkstation.value = data.monitoring_type === "workstation" && data.plat === "windows";
        agentHostname.value = data.hostname || "";
        agentPlat.value = data.plat || "windows";
        natsOnline.value = typeof data.nats_online === "boolean" ? data.nats_online : null;
        meshConnected.value = typeof data.mesh_connected === "boolean" ? data.mesh_connected : null;
        meshServiceStatus.value = data.mesh_service_status || "";
        diagnosticReason.value = data.diagnostic_reason || "";
        iframeKey.value += 1;

        useMeta({
          title: `${data.hostname} - ${data.client} - ${data.site} | Take Control`,
        });

        // If NATS is reachable but Mesh binary/registration is broken/missing, attempt 1 auto-repair seamlessly
        if (data.nats_online && data.mesh_connected === false && data.needs_recovery && !autoRepairTried) {
          autoRepairTried = true;
          $q.loading.show({ message: "Mesh Agent dessincronizado — executando reparo automático..." });
          try {
            await sendAgentRecoverMesh(params.agent_id);
            const retried = await fetchAgentMeshCentralURLs(params.agent_id);
            if (retried) {
              control.value = retried.control;
              status.value = retried.status;
              natsOnline.value = typeof retried.nats_online === "boolean" ? retried.nats_online : null;
              meshConnected.value = typeof retried.mesh_connected === "boolean" ? retried.mesh_connected : null;
              meshServiceStatus.value = retried.mesh_service_status || "";
              diagnosticReason.value = retried.diagnostic_reason || "";
              iframeKey.value += 1;
            }
          } catch (recErr) {
            console.error(recErr);
          }
        }
      } catch (e) {
        console.error(e);
        meshConnected.value = false;
        diagnosticReason.value = "Erro ao conectar ao endpoint de Controle Remoto.";
      } finally {
        loadingConn.value = false;
        $q.loading.hide();
      }
    }

    async function getDashInfo() {
      const { dark_mode, loading_bar_color } = await fetchDashboardInfo();
      syncDarkModeWithSavedPalette(dark_mode);
      $q.loadingBar.setDefaults({ color: loading_bar_color });
    }

    async function repairMeshCentral() {
      didPauseOnExit = false;
      control.value = "";
      $q.loading.show({ message: "Reparando e sincronizando Mesh Agent..." });
      try {
        const data = await sendAgentRecoverMesh(params.agent_id);
        await getMeshURLs();
        setTimeout(() => {
          notifySuccess(data);
        }, 300);
      } catch (e) {
        console.error(e);
        notifyError("Não foi possível contatar o agente via NATS para recuperar o Mesh.");
      }
      $q.loading.hide();
    }

    async function restartMeshService() {
      didPauseOnExit = false;
      $q.loading.show({ message: "Reiniciando serviço Mesh Agent..." });
      try {
        if (agentPlat.value === "windows") {
          await sendAgentServiceAction(params.agent_id, "mesh agent", { sv_action: "restart" });
        } else {
          await sendAgentRecoverMesh(params.agent_id);
        }
        control.value = "";
        await new Promise((resolve) => setTimeout(resolve, 1500));
        await getMeshURLs();
        if (meshConnected.value !== false) {
          notifySuccess("Serviço Mesh Agent reiniciado e conectado!");
        }
      } catch (e) {
        console.error(e);
        notifyError("Falha ao reiniciar o Mesh Agent.");
      }
      $q.loading.hide();
    }

    async function connectNativeRDP() {
      rdpConnecting.value = true;
      let rdpConfirmed = false;
      try {
        await manageAgentRDP(params.agent_id, "enable_rdp", false);
        rdpConfirmed = true;
      } catch (e) {
        rdpConfirmed = false;
      }
      try {
        const agentData = await fetchAgent(params.agent_id);
        const targetHost = resolveFirstReachableHost(
          agentData?.local_ips || agentData?.local_ip,
          agentData?.hostname || agentHostname.value,
          agentData?.public_ip,
        );
        const hostLabel = agentData?.hostname || agentHostname.value || "workstation";
        downloadNativeRDPFile(hostLabel, targetHost, 3389);
        if (rdpConfirmed) {
          notifySuccess(`RDP habilitado em ${hostLabel} (${targetHost}) e arquivo .rdp baixado!`);
        } else {
          notifyWarning(
            `Agente não respondeu via NATS para ativar o TermService; arquivo ${hostLabel}.rdp baixado com IP ${targetHost}.`,
          );
        }
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
        didPauseOnExit = true;
        meshConnected.value = false;
        diagnosticReason.value = "Mesh Agent pausado em Modo Banco (Sob Demanda). Clique em 'Testar e Reconectar' quando desejar reassumir a tela.";
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
      natsOnline,
      meshConnected,
      meshServiceStatus,
      diagnosticReason,
      loadingConn,
      forceShowIframe,
      iframeKey,
      agentPlat,

      // methods
      getMeshURLs,
      repairMeshCentral,
      restartMeshService,
      connectNativeRDP,
      pauseMeshForBanking,
    };
  },
};
</script>
