<template>
  <q-list dense style="min-width: 200px">
    <!-- edit agent -->
    <q-item clickable v-close-popup @click="showEditAgent(agent.agent_id)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-edit" />
      </q-item-section>
      <q-item-section>{{ t("menu.edit") }} {{ agent.hostname }}</q-item-section>
    </q-item>
    <!-- agent pending actions -->
    <q-item clickable v-close-popup @click="showPendingActionsModal(agent)">
      <q-item-section side>
        <q-icon size="xs" name="far fa-clock" />
      </q-item-section>
      <q-item-section>{{ t("menu.pendingActions") }}</q-item-section>
    </q-item>
    <!-- take control -->
    <q-item
      clickable
      v-ripple
      v-close-popup
      @click="runTakeControl(agent.agent_id)"
    >
      <q-item-section side>
        <q-icon size="xs" name="fas fa-desktop" />
      </q-item-section>

      <q-item-section>{{ t("menu.takeControl") }}</q-item-section>
    </q-item>

    <!-- vnc -->
    <q-item
      clickable
      v-ripple
      v-close-popup
      @click="launchWebVNC(agent.agent_id)"
    >
      <q-item-section side>
        <q-icon size="xs" name="screen_share" />
      </q-item-section>

      <q-item-section>VNC</q-item-section>
    </q-item>

    <q-item clickable v-ripple :disable="urlActions.length === 0">
      <q-item-section side>
        <q-icon size="xs" name="open_in_new" />
      </q-item-section>
      <q-item-section>{{ t("menu.runUrlAction") }}</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>
      <q-menu auto-close anchor="top end" self="top start">
        <q-list>
          <q-item
            v-for="action in urlActions"
            :key="action.id"
            dense
            clickable
            v-close-popup
            @click="
              runURLAction({ agent_id: agent.agent_id, action: action.id })
            "
          >
            <q-item-section>{{ action.name }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-ripple v-close-popup @click="showSendCommand(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-terminal" />
      </q-item-section>
      <q-item-section>{{ t("menu.sendCommand") }}</q-item-section>
    </q-item>

    <q-item clickable v-ripple v-close-popup @click="showRunScript(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-terminal" />
      </q-item-section>
      <q-item-section>{{ t("menu.runScript") }}</q-item-section>
    </q-item>

    <q-item clickable v-ripple :disable="favoriteScripts.length === 0">
      <q-item-section side>
        <q-icon size="xs" name="star" />
      </q-item-section>
      <q-item-section>{{ t("menu.runFavScript") }}</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>
      <q-menu auto-close anchor="top end" self="top start">
        <q-list>
          <q-item
            v-for="script in favoriteScripts"
            :key="script.value"
            dense
            clickable
            v-close-popup
            @click="showRunScript(agent, script.value)"
          >
            <q-item-section>{{ script.label }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item
      clickable
      v-close-popup
      @click="runRemoteBackground(agent.agent_id, agent.plat)"
    >
      <q-item-section side>
        <q-icon size="xs" name="terminal" />
      </q-item-section>
      <q-item-section>{{ t("menu.remoteBg") }}</q-item-section>
    </q-item>

    <!-- maintenance mode -->
    <q-item clickable v-close-popup @click="toggleMaintenance(agent)">
      <q-item-section side>
        <q-icon size="xs" name="construction" />
      </q-item-section>
      <q-item-section>
        {{
          agent.maintenance_mode
            ? t("menu.disableMaint")
            : t("menu.enableMaint")
        }}
      </q-item-section>
    </q-item>

    <!-- patch management -->
    <q-item clickable>
      <q-item-section side>
        <q-icon size="xs" name="system_update" />
      </q-item-section>
      <q-item-section>{{ t("menu.patchMgmt") }}</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>

      <q-menu auto-close anchor="top right" self="top left">
        <q-list dense style="min-width: 100px">
          <q-item clickable v-ripple @click="runPatchStatusScan(agent)">
            <q-item-section>{{ t("menu.scanPatches") }}</q-item-section>
          </q-item>
          <q-item clickable v-ripple @click="installPatches(agent)">
            <q-item-section>{{ t("menu.installPatches") }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-close-popup @click="runChecks(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-check-double" />
      </q-item-section>
      <q-item-section>{{ t("menu.runChecks") }}</q-item-section>
    </q-item>

    <!-- Ferramentas Equipe de TI -->
    <q-item clickable>
      <q-item-section side>
        <q-icon size="xs" name="build" />
      </q-item-section>
      <q-item-section>{{ t("menu.enhancedTools") }}</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>
      <q-menu auto-close anchor="top right" self="top left">
        <q-list dense style="min-width: 220px">
          <q-item clickable v-ripple @click="quickDownloadRDP(agent)">
            <q-item-section side>
              <q-icon size="xs" name="computer" color="primary" />
            </q-item-section>
            <q-item-section>Conectar / Baixar .RDP (1-Clique)</q-item-section>
          </q-item>
          <q-item clickable v-ripple @click="quickEnableRDP(agent)">
            <q-item-section side>
              <q-icon size="xs" name="lock_open" color="positive" />
            </q-item-section>
            <q-item-section>Habilitar RDP Seguro (NLA)</q-item-section>
          </q-item>
          <q-separator />
          <q-item clickable v-ripple @click="quickAdminAction(agent, 'gpupdate_force')">
            <q-item-section side>
              <q-icon size="xs" name="policy" color="info" />
            </q-item-section>
            <q-item-section>Forçar GPO (gpupdate /force)</q-item-section>
          </q-item>
          <q-item clickable v-ripple @click="quickAdminAction(agent, 'clear_print_spooler')">
            <q-item-section side>
              <q-icon size="xs" name="print" color="teal" />
            </q-item-section>
            <q-item-section>Resetar Spooler de Impressão</q-item-section>
          </q-item>
          <q-item clickable v-ripple @click="quickSelfHeal(agent, 'disk_cleanup', 'disk')">
            <q-item-section side>
              <q-icon size="xs" name="cleaning_services" color="amber-8" />
            </q-item-section>
            <q-item-section>Limpar Arquivos Temporários</q-item-section>
          </q-item>
          <q-separator />
          <q-item clickable v-ripple @click="quickSendUserNotice(agent)">
            <q-item-section side>
              <q-icon size="xs" name="campaign" color="orange" />
            </q-item-section>
            <q-item-section>Enviar Aviso TI na Tela</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-close-popup @click="wakeUp(agent)">
      <q-item-section side>
        <q-icon size="xs" name="offline_bolt" />
      </q-item-section>
      <q-item-section>{{ t("menu.wakeUp") }}</q-item-section>
    </q-item>

    <q-item clickable>
      <q-item-section side>
        <q-icon size="xs" name="power_settings_new" />
      </q-item-section>
      <q-item-section>{{ t("menu.reboot") }}</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>

      <q-menu auto-close anchor="top right" self="top left">
        <q-list dense style="min-width: 100px">
          <!-- reboot now -->
          <q-item clickable v-ripple @click="rebootNow(agent)">
            <q-item-section>{{ t("menu.rebootNow") }}</q-item-section>
          </q-item>
          <!-- reboot later -->
          <q-item clickable v-ripple @click="showRebootLaterModal(agent)">
            <q-item-section>{{ t("menu.rebootLater") }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-item>

    <q-item clickable v-close-popup @click="shutdown(agent)">
      <q-item-section side>
        <q-icon size="xs" name="power" />
      </q-item-section>
      <q-item-section>{{ t("menu.shutdown") }}</q-item-section>
    </q-item>

    <q-item clickable v-close-popup @click="showPolicyAdd(agent)">
      <q-item-section side>
        <q-icon size="xs" name="policy" />
      </q-item-section>
      <q-item-section>{{ t("menu.assignPolicy") }}</q-item-section>
    </q-item>

    <q-item
      clickable
      v-if="
        $integrations &&
        $integrations.agentMenuIntegrations &&
        $integrations.agentMenuIntegrations.length > 0
      "
    >
      <q-item-section side>
        <q-icon size="xs" name="analytics" />
      </q-item-section>
      <q-item-section>{{ t("filebar.reporting") }}</q-item-section>
      <q-item-section side>
        <q-icon name="keyboard_arrow_right" />
      </q-item-section>
      <integrations-context-menu type="agent" :id="agent.agent_id" />
    </q-item>

    <q-item clickable v-close-popup @click="showAgentRecovery(agent)">
      <q-item-section side>
        <q-icon size="xs" name="fas fa-first-aid" />
      </q-item-section>
      <q-item-section>{{ t("menu.agentRecovery") }}</q-item-section>
    </q-item>

    <q-item clickable v-close-popup @click="pingAgent(agent)">
      <q-item-section side>
        <q-icon size="xs" name="delete" />
      </q-item-section>
      <q-item-section>{{ t("menu.removeAgent") }}</q-item-section>
    </q-item>

    <q-separator />
    <q-item clickable v-close-popup>
      <q-item-section>Close</q-item-section>
    </q-item>
  </q-list>
</template>

<script>
// composition imports
import { ref, inject, onMounted } from "vue";
import { useStore } from "vuex";
import { useQuasar } from "quasar";
import { t } from "@/i18n";
import { fetchURLActions, runURLAction } from "@/api/core";
import {
  editAgent,
  agentRebootNow,
  agentShutdown,
  sendAgentPing,
  removeAgent,
  runRemoteBackground,
  runTakeControl,
  runWebVNC,
  wakeUpWOL,
} from "@/api/agents";
import { runAgentUpdateScan, runAgentUpdateInstall } from "@/api/winupdates";
import { runAgentChecks } from "@/api/checks";
import { fetchScripts } from "@/api/scripts";
import {
  triggerAgentSelfHeal,
  runAgentWingetOperation,
  repairAgentHALink,
  manageAgentRDP,
  downloadNativeRDPFile,
  runAgentAdminAction,
  sendAgentITSupportMessage,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

// ui imports
import PendingActions from "@/components/logs/PendingActions.vue";
import AgentRecovery from "@/components/modals/agents/AgentRecovery.vue";
import PolicyAdd from "@/components/automation/modals/PolicyAdd.vue";
import RebootLater from "@/components/modals/agents/RebootLater.vue";
import EditAgent from "@/components/modals/agents/EditAgent.vue";
import SendCommand from "@/components/modals/agents/SendCommand.vue";
import RunScript from "@/components/modals/agents/RunScript.vue";
import IntegrationsContextMenu from "@/components/ui/IntegrationsContextMenu.vue";
import ConfirmYesDialog from "@/components/agents/ConfirmYesDialog.vue";

export default {
  name: "AgentActionMenu",
  components: {
    IntegrationsContextMenu,
  },
  props: {
    agent: !Object,
  },
  setup() {
    // setup quasar
    const $q = useQuasar();

    // setup vuex
    const store = useStore();

    const refreshDashboard = inject("refreshDashboard");

    const urlActions = ref([]);
    const favoriteScripts = ref([]);

    function showEditAgent(agent_id) {
      $q.dialog({
        component: EditAgent,
        componentProps: {
          agent_id: agent_id,
        },
      }).onOk(refreshDashboard);
    }

    function showPendingActionsModal(agent) {
      $q.dialog({
        component: PendingActions,
        componentProps: {
          agent: agent,
        },
      });
    }

    async function getURLActions() {
      try {
        urlActions.value = (await fetchURLActions())
          .filter((action) => action.action_type === "web")
          .sort((a, b) => a.name.localeCompare(b.name));
      } catch (e) {
        console.error(e);
      }
    }

    function showSendCommand(agent) {
      $q.dialog({
        component: SendCommand,
        componentProps: {
          agent: agent,
        },
      });
    }

    function showRunScript(agent, script = undefined) {
      $q.dialog({
        component: RunScript,
        componentProps: {
          agent,
          script,
        },
      });
    }

    async function getFavoriteScripts() {
      favoriteScripts.value = [];

      try {
        const data = await fetchScripts({
          showCommunityScripts: store.state.showCommunityScripts,
        });

        const scripts = data.filter((script) => !!script.favorite);

        favoriteScripts.value = scripts
          .map((script) => ({
            label: script.name,
            value: script.id,
            timeout: script.default_timeout,
            args: script.args,
          }))
          .sort((a, b) => a.label.localeCompare(b.label));
      } catch (e) {
        console.error(e);
      }
    }

    async function toggleMaintenance(agent) {
      let data = {
        maintenance_mode: !agent.maintenance_mode,
      };

      try {
        await editAgent(agent.agent_id, data);
        notifySuccess(
          `Maintenance mode was ${
            agent.maintenance_mode ? "disabled" : "enabled"
          } on ${agent.hostname}`,
        );
        store.commit("setRefreshSummaryTab", true);
        refreshDashboard();
      } catch (e) {
        console.error(e);
      }
    }

    async function runPatchStatusScan(agent) {
      try {
        await runAgentUpdateScan(agent.agent_id);
        notifySuccess(`Scan will be run shortly on ${agent.hostname}`);
      } catch (e) {
        console.error(e);
      }
    }

    async function installPatches(agent) {
      try {
        const data = await runAgentUpdateInstall(agent.agent_id);
        notifySuccess(data);
      } catch (e) {
        console.error(e);
      }
    }

    async function runChecks(agent) {
      try {
        const data = await runAgentChecks(agent.agent_id);
        notifySuccess(data);
      } catch (e) {
        console.error(e);
      }
    }

    async function wakeUp(agent) {
      try {
        const data = await wakeUpWOL(agent.agent_id);
        notifySuccess(data);
      } catch (e) {
        console.error(e);
      }
    }

    function showRebootLaterModal(agent) {
      $q.dialog({
        component: RebootLater,
        componentProps: {
          agent: agent,
        },
      }).onOk(refreshDashboard);
    }

    function launchWebVNC(agent_id) {
      $q.dialog({
        title: "VNC Server Port",
        message: "Enter the VNC server port:",
        prompt: {
          model: "5900",
          type: "text",
        },
        cancel: true,
        ok: { label: "Launch", color: "primary" },
        persistent: true,
      }).onOk((port) => {
        runWebVNC(agent_id, port);
      });
    }

    function rebootNow(agent) {
      $q.dialog({
        title: "Are you sure?",
        message: `Reboot ${agent.hostname} now`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        $q.loading.show();
        try {
          await agentRebootNow(agent.agent_id);
          notifySuccess(`${agent.hostname} will now be restarted`);
          $q.loading.hide();
        } catch (e) {
          $q.loading.hide();
          console.error(e);
        }
      });
    }

    function shutdown(agent) {
      $q.dialog({
        component: ConfirmYesDialog,
        componentProps: {
          hostname: agent.hostname,
          actionVerb: "shutdown",
          title: "Confirm Shutdown",
          okLabel: "Shutdown",
          okColor: "negative",
        },
      }).onOk(async () => {
        $q.loading.show();
        try {
          await agentShutdown(agent.agent_id);
          notifySuccess(`${agent.hostname} will now be shutdown`);
          $q.loading.hide();
        } catch (e) {
          $q.loading.hide();
          console.error(e);
        }
      });
    }

    function showPolicyAdd(agent) {
      $q.dialog({
        component: PolicyAdd,
        componentProps: {
          type: "agent",
          object: agent,
        },
      }).onOk(refreshDashboard);
    }

    function showAgentRecovery(agent) {
      $q.dialog({
        component: AgentRecovery,
        componentProps: {
          agent: agent,
        },
      });
    }

    async function pingAgent(agent) {
      try {
        $q.loading.show();
        const data = await sendAgentPing(agent.agent_id);
        $q.loading.hide();
        if (data.status === "offline") {
          $q.dialog({
            title: "Agent offline",
            message: `${agent.hostname} cannot be contacted.
                  Would you like to continue with the uninstall?
                  If so, the agent will need to be manually uninstalled from the computer.`,
            cancel: { label: "No", color: "negative" },
            ok: { label: "Yes", color: "positive" },
            persistent: true,
          })
            .onOk(() => deleteAgent(agent))
            .onCancel(() => {
              return;
            });
        } else if (data.status === "online") {
          deleteAgent(agent);
        } else {
          notifyError("Something went wrong");
        }
      } catch (e) {
        $q.loading.hide();
        console.error(e);
      }
    }

    function deleteAgent(agent) {
      $q.dialog({
        component: ConfirmYesDialog,
        componentProps: {
          hostname: agent.hostname,
          actionVerb: "deletion",
          title: "Confirm Deletion",
          okLabel: "Uninstall",
          okColor: "negative",
        },
      }).onOk(async () => {
        try {
          const data = await removeAgent(agent.agent_id);
          notifySuccess(data);
          refreshDashboard(
            false /* clearTreeSelected */,
            true /* clearSubTable */,
          );
        } catch (e) {
          console.error(e);
        }
      });
    }

    onMounted(async () => {
      await getURLActions();
      await getFavoriteScripts();
    });

    async function quickSelfHeal(agent, action, mode) {
      try {
        await triggerAgentSelfHeal(agent.agent_id, action, mode);
        notifySuccess(`Self-healing (${action}:${mode}) triggered on ${agent.hostname}`);
      } catch (e) {
        notifyError(e?.response?.data?.error || "Failed to trigger self-healing");
      }
    }

    async function quickWingetUpgrade(agent) {
      try {
        await runAgentWingetOperation(agent.agent_id, "upgrade", "all");
        notifySuccess(`Winget upgrade-all triggered on ${agent.hostname}`);
      } catch (e) {
        notifyError(e?.response?.data?.error || "Failed to trigger Winget upgrade");
      }
    }

    async function quickRepairHALink(agent) {
      try {
        await repairAgentHALink(agent.agent_id);
        notifySuccess(`Link HA & Serviço Mesh ressincronizados em ${agent.hostname}`);
      } catch (e) {
        notifyError(e?.response?.data?.error || "Falha ao reparar Link/Mesh");
      }
    }

    async function quickEnableRDP(agent) {
      try {
        await manageAgentRDP(agent.agent_id, "enable_rdp", true);
        notifySuccess(`RDP Seguro (NLA) habilitado em ${agent.hostname}`);
      } catch (e) {
        notifyError(e?.response?.data?.error || "Falha ao habilitar RDP");
      }
    }

    function quickDownloadRDP(agent) {
      const targetIp = agent.local_ips || agent.hostname || agent.public_ip || "127.0.0.1";
      downloadNativeRDPFile(agent.hostname || targetIp, targetIp, 3389);
      notifySuccess(`Arquivo ${agent.hostname || targetIp}.rdp baixado!`);
    }

    async function quickAdminAction(agent, action) {
      try {
        const res = await runAgentAdminAction(agent.agent_id, action);
        notifySuccess(res?.steps?.[0] || `Ação (${action}) concluída em ${agent.hostname}`);
      } catch (e) {
        notifyError(e?.response?.data?.error || `Falha ao executar ${action}`);
      }
    }

    function quickSendUserNotice(agent) {
      $q.dialog({
        title: `Aviso de Suporte TI — ${agent.hostname}`,
        message: "Digite a mensagem que será exibida na tela do usuário:",
        prompt: {
          model: "Olá! A equipe de TI está realizando uma manutenção rápida no seu computador.",
          type: "text",
        },
        cancel: true,
      }).onOk(async (text) => {
        if (!text) return;
        try {
          await sendAgentITSupportMessage(agent.agent_id, "Suporte de TI", text, 60);
          notifySuccess(`Mensagem enviada para ${agent.hostname}!`);
        } catch (e) {
          notifyError(e?.response?.data?.error || "Falha ao enviar mensagem");
        }
      });
    }

    return {
      // reactive data
      urlActions,
      favoriteScripts,

      // methods
      showEditAgent,
      showPendingActionsModal,
      runTakeControl,
      runRemoteBackground,
      getURLActions,
      runURLAction,
      showSendCommand,
      showRunScript,
      getFavoriteScripts,
      toggleMaintenance,
      runPatchStatusScan,
      installPatches,
      runChecks,
      showRebootLaterModal,
      rebootNow,
      shutdown,
      showPolicyAdd,
      showAgentRecovery,
      pingAgent,
      wakeUp,
      launchWebVNC,
      quickSelfHeal,
      quickWingetUpgrade,
      quickRepairHALink,
      quickEnableRDP,
      quickDownloadRDP,
      quickAdminAction,
      quickSendUserNotice,
      t,
    };
  },
};
</script>
