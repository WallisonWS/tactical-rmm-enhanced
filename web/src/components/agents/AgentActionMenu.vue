<template>
  <div class="trmm-agent-menu column no-wrap">
    <!-- Sticky Hostname Header -->
    <div
      class="trmm-am-header row items-center justify-between no-wrap q-px-md q-py-xs"
      :class="$q.dark.isActive ? 'trmm-am-header--dark' : 'trmm-am-header--light'"
    >
      <div class="row items-center no-wrap" style="gap: 7px; min-width: 0">
        <span
          class="trmm-am-dot"
          :class="
            agent.status === 'overdue'
              ? 'trmm-am-dot--negative'
              : agent.status === 'offline'
                ? 'trmm-am-dot--warning'
                : 'trmm-am-dot--positive'
          "
        />
        <span class="text-caption text-weight-bold ellipsis">{{ agent.hostname }}</span>
      </div>
      <q-btn dense flat round size="xs" icon="close" color="grey-5" v-close-popup />
    </div>

    <!-- Single-Layer Scrollable Action List -->
    <div class="trmm-am-body trmm-menu-scroll">
      <q-list dense class="q-py-xs">
        <!-- Section: Remote Access -->
        <div class="trmm-am-section-label">Acesso Remoto</div>

        <q-item
          clickable
          v-ripple
          v-close-popup
          class="trmm-am-item"
          @click="runTakeControl(agent.agent_id)"
        >
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--blue">
              <q-icon size="15px" name="connected_tv" />
            </div>
          </q-item-section>
          <q-item-section class="text-weight-medium">{{ t("menu.takeControl") }}</q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          v-close-popup
          class="trmm-am-item"
          @click="launchWebVNC(agent.agent_id)"
        >
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--sky">
              <q-icon size="15px" name="cast_connected" />
            </div>
          </q-item-section>
          <q-item-section>VNC</q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          v-close-popup
          class="trmm-am-item"
          @click="runRemoteBackground(agent.agent_id, agent.plat)"
        >
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--teal">
              <q-icon size="15px" name="terminal" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.remoteBg") }}</q-item-section>
        </q-item>

        <q-item clickable v-ripple class="trmm-am-item">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--sky">
              <q-icon size="15px" name="open_in_new" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.runUrlAction") }}</q-item-section>
          <q-item-section side>
            <q-icon size="16px" name="chevron_right" color="grey-5" />
          </q-item-section>
          <q-menu auto-close anchor="top end" self="top start" class="trmm-popover-menu">
            <q-list dense style="min-width: 230px" class="q-py-xs">
              <q-item
                v-for="action in urlActions"
                :key="action.id"
                dense
                clickable
                v-close-popup
                class="trmm-am-item"
                @click="
                  runURLAction({ agent_id: agent.agent_id, action: action.id })
                "
              >
                <q-item-section side>
                  <q-icon size="15px" name="link" color="primary" />
                </q-item-section>
                <q-item-section>{{ action.name }}</q-item-section>
              </q-item>
              <q-item
                v-if="urlActions.length === 0"
                dense
                clickable
                v-close-popup
                class="trmm-am-item"
                @click="openGlobalSettingsModal"
              >
                <q-item-section side>
                  <q-icon size="15px" name="settings" color="primary" />
                </q-item-section>
                <q-item-section>Cadastrar Ações de URL (Configurações Globais)</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-item>

        <q-separator class="q-my-xs trmm-am-sep" />

        <!-- Section: Commands & Automation -->
        <div class="trmm-am-section-label">Comandos &amp; Automação</div>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="showSendCommand(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--indigo">
              <q-icon size="15px" name="code" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.sendCommand") }}</q-item-section>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="showRunScript(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--purple">
              <q-icon size="15px" name="play_circle_outline" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.runScript") }}</q-item-section>
        </q-item>

        <q-item clickable v-ripple class="trmm-am-item">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--amber">
              <q-icon size="15px" name="star_outline" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.runFavScript") }}</q-item-section>
          <q-item-section side>
            <q-icon size="16px" name="chevron_right" color="grey-5" />
          </q-item-section>
          <q-menu auto-close anchor="top end" self="top start" class="trmm-popover-menu">
            <q-list dense style="min-width: 230px" class="q-py-xs">
              <q-item
                v-for="script in favoriteScripts"
                :key="script.value"
                dense
                clickable
                v-close-popup
                class="trmm-am-item"
                @click="showRunScript(agent, script.value)"
              >
                <q-item-section side>
                  <q-icon size="15px" name="star" color="amber-5" />
                </q-item-section>
                <q-item-section>{{ script.label }}</q-item-section>
              </q-item>
              <q-item
                v-if="favoriteScripts.length === 0"
                dense
                clickable
                v-close-popup
                class="trmm-am-item"
                @click="openScriptManagerModal"
              >
                <q-item-section side>
                  <q-icon size="15px" name="star" color="amber" />
                </q-item-section>
                <q-item-section>Marcar Scripts Favoritos (Gerenciador de Scripts)</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="runChecks(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--emerald">
              <q-icon size="15px" name="task_alt" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.runChecks") }}</q-item-section>
        </q-item>

        <!-- Ferramentas Equipe de TI -->
        <q-item clickable v-ripple class="trmm-am-item">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--teal">
              <q-icon size="15px" name="handyman" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.enhancedTools") }}</q-item-section>
          <q-item-section side>
            <q-icon size="16px" name="chevron_right" color="grey-5" />
          </q-item-section>
          <q-menu auto-close anchor="top right" self="top left" class="trmm-popover-menu">
            <q-list dense style="min-width: 245px" class="q-py-xs">
              <q-item clickable v-ripple class="trmm-am-item" @click="quickDownloadRDP(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="cast_connected" color="primary" />
                </q-item-section>
                <q-item-section>Conectar / Baixar .RDP (1-Clique)</q-item-section>
              </q-item>
              <q-item clickable v-ripple class="trmm-am-item" @click="quickEnableRDP(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="lock_open" color="positive" />
                </q-item-section>
                <q-item-section>Habilitar RDP Seguro (NLA)</q-item-section>
              </q-item>
              <q-separator class="q-my-xs" />
              <q-item clickable v-ripple class="trmm-am-item" @click="quickAdminAction(agent, 'gpupdate_force')">
                <q-item-section side>
                  <q-icon size="16px" name="policy" color="info" />
                </q-item-section>
                <q-item-section>Forçar GPO (gpupdate /force)</q-item-section>
              </q-item>
              <q-item clickable v-ripple class="trmm-am-item" @click="quickAdminAction(agent, 'clear_print_spooler')">
                <q-item-section side>
                  <q-icon size="16px" name="print" color="teal" />
                </q-item-section>
                <q-item-section>Resetar Spooler de Impressão</q-item-section>
              </q-item>
              <q-item clickable v-ripple class="trmm-am-item" @click="quickSelfHeal(agent, 'disk_cleanup', 'disk')">
                <q-item-section side>
                  <q-icon size="16px" name="cleaning_services" color="amber-8" />
                </q-item-section>
                <q-item-section>Limpar Arquivos Temporários</q-item-section>
              </q-item>
              <q-separator class="q-my-xs" />
              <q-item clickable v-ripple class="trmm-am-item" @click="quickSendUserNotice(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="campaign" color="orange" />
                </q-item-section>
                <q-item-section>Enviar Aviso TI na Tela</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-item>

        <q-separator class="q-my-xs trmm-am-sep" />

        <!-- Section: Maintenance & Patches -->
        <div class="trmm-am-section-label">Manutenção &amp; Patches</div>

        <q-item clickable v-ripple class="trmm-am-item">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--blue">
              <q-icon size="15px" name="system_update_alt" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.patchMgmt") }}</q-item-section>
          <q-item-section side>
            <q-icon size="16px" name="chevron_right" color="grey-5" />
          </q-item-section>

          <q-menu auto-close anchor="top right" self="top left" class="trmm-popover-menu">
            <q-list dense style="min-width: 195px" class="q-py-xs">
              <q-item clickable v-ripple class="trmm-am-item" @click="runPatchStatusScan(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="manage_search" color="primary" />
                </q-item-section>
                <q-item-section>{{ t("menu.scanPatches") }}</q-item-section>
              </q-item>
              <q-item clickable v-ripple class="trmm-am-item" @click="installPatches(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="download_for_offline" color="positive" />
                </q-item-section>
                <q-item-section>{{ t("menu.installPatches") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="toggleMaintenance(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--amber">
              <q-icon size="15px" name="engineering" />
            </div>
          </q-item-section>
          <q-item-section>
            {{
              agent.maintenance_mode
                ? t("menu.disableMaint")
                : t("menu.enableMaint")
            }}
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="showPendingActionsModal(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--orange">
              <q-icon size="15px" name="pending_actions" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.pendingActions") }}</q-item-section>
        </q-item>

        <q-separator class="q-my-xs trmm-am-sep" />

        <!-- Section: Power -->
        <div class="trmm-am-section-label">Energia</div>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="wakeUp(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--emerald">
              <q-icon size="15px" name="bolt" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.wakeUp") }}</q-item-section>
        </q-item>

        <q-item clickable v-ripple class="trmm-am-item">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--orange">
              <q-icon size="15px" name="restart_alt" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.reboot") }}</q-item-section>
          <q-item-section side>
            <q-icon size="16px" name="chevron_right" color="grey-5" />
          </q-item-section>

          <q-menu auto-close anchor="top right" self="top left" class="trmm-popover-menu">
            <q-list dense style="min-width: 185px" class="q-py-xs">
              <q-item clickable v-ripple class="trmm-am-item" @click="rebootNow(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="flash_on" color="orange" />
                </q-item-section>
                <q-item-section>{{ t("menu.rebootNow") }}</q-item-section>
              </q-item>
              <q-item clickable v-ripple class="trmm-am-item" @click="showRebootLaterModal(agent)">
                <q-item-section side>
                  <q-icon size="16px" name="schedule" color="primary" />
                </q-item-section>
                <q-item-section>{{ t("menu.rebootLater") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item trmm-am-item--danger" @click="shutdown(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--red">
              <q-icon size="15px" name="power_settings_new" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.shutdown") }}</q-item-section>
        </q-item>

        <q-separator class="q-my-xs trmm-am-sep" />

        <!-- Section: Administration -->
        <div class="trmm-am-section-label">Administração</div>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="showEditAgent(agent.agent_id)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--slate">
              <q-icon size="15px" name="tune" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.edit") }} {{ agent.hostname }}</q-item-section>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="showPolicyAdd(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--purple">
              <q-icon size="15px" name="policy" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.assignPolicy") }}</q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          class="trmm-am-item"
          v-if="
            $integrations &&
            $integrations.agentMenuIntegrations &&
            $integrations.agentMenuIntegrations.length > 0
          "
        >
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--sky">
              <q-icon size="15px" name="analytics" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("filebar.reporting") }}</q-item-section>
          <q-item-section side>
            <q-icon size="16px" name="chevron_right" color="grey-5" />
          </q-item-section>
          <integrations-context-menu type="agent" :id="agent.agent_id" />
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item" @click="showAgentRecovery(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--teal">
              <q-icon size="15px" name="medical_services" />
            </div>
          </q-item-section>
          <q-item-section>{{ t("menu.agentRecovery") }}</q-item-section>
        </q-item>

        <q-item clickable v-ripple v-close-popup class="trmm-am-item trmm-am-item--danger" @click="pingAgent(agent)">
          <q-item-section side>
            <div class="trmm-am-icon trmm-am-icon--red">
              <q-icon size="15px" name="delete_outline" />
            </div>
          </q-item-section>
          <q-item-section class="text-red-4 text-weight-medium">{{ t("menu.removeAgent") }}</q-item-section>
        </q-item>
      </q-list>
    </div>
  </div>
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
  resolveFirstReachableHost,
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
import ScriptManager from "@/components/scripts/ScriptManager.vue";
import EditCoreSettings from "@/components/modals/coresettings/EditCoreSettings.vue";
import DialogWrapper from "@/components/ui/DialogWrapper.vue";
import IntegrationsContextMenu from "@/components/ui/IntegrationsContextMenu.vue";
import ConfirmYesDialog from "@/components/agents/ConfirmYesDialog.vue";

const ACTION_MENU_CACHE_TTL_MS = 60_000;
let _urlActionsCache = null;
let _urlActionsCacheAt = 0;
let _urlActionsInflight = null;
let _favScriptsCache = null;
let _favScriptsCacheKey = null;
let _favScriptsCacheAt = 0;
let _favScriptsInflight = null;

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
      const now = Date.now();
      if (_urlActionsCache && now - _urlActionsCacheAt < ACTION_MENU_CACHE_TTL_MS) {
        urlActions.value = _urlActionsCache;
        return;
      }
      try {
        if (!_urlActionsInflight) {
          _urlActionsInflight = fetchURLActions()
            .then((list) => {
              const filtered = list
                .filter((action) => action.action_type === "web")
                .sort((a, b) => a.name.localeCompare(b.name));
              _urlActionsCache = filtered;
              _urlActionsCacheAt = Date.now();
              return filtered;
            })
            .finally(() => {
              _urlActionsInflight = null;
            });
        }
        urlActions.value = await _urlActionsInflight;
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

    function openScriptManagerModal() {
      $q.dialog({
        component: DialogWrapper,
        componentProps: {
          vuecomponent: ScriptManager,
          dialogProps: {
            fullWidth: true,
            fullHeight: true,
          },
        },
      });
    }

    function openGlobalSettingsModal() {
      $q.dialog({
        component: EditCoreSettings,
      });
    }

    async function getFavoriteScripts() {
      const showComm = !!store.state.showCommunityScripts;
      const now = Date.now();
      if (
        _favScriptsCache &&
        _favScriptsCacheKey === showComm &&
        now - _favScriptsCacheAt < ACTION_MENU_CACHE_TTL_MS
      ) {
        favoriteScripts.value = _favScriptsCache;
        return;
      }

      try {
        if (!_favScriptsInflight || _favScriptsCacheKey !== showComm) {
          _favScriptsCacheKey = showComm;
          _favScriptsInflight = fetchScripts({
            showCommunityScripts: showComm,
          })
            .then((data) => {
              const mapped = data
                .filter((script) => !!script.favorite)
                .map((script) => ({
                  label: script.name,
                  value: script.id,
                  timeout: script.default_timeout,
                  args: script.args,
                }))
                .sort((a, b) => a.label.localeCompare(b.label));
              _favScriptsCache = mapped;
              _favScriptsCacheAt = Date.now();
              return mapped;
            })
            .finally(() => {
              _favScriptsInflight = null;
            });
        }
        favoriteScripts.value = await _favScriptsInflight;
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

    onMounted(() => {
      Promise.all([getURLActions(), getFavoriteScripts()]);
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
      const targetIp = resolveFirstReachableHost(agent.local_ips, agent.hostname, agent.public_ip);
      downloadNativeRDPFile(agent.hostname || targetIp, targetIp, 3389);
      notifySuccess(`Arquivo ${agent.hostname || targetIp}.rdp baixado (${targetIp})!`);
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
      openScriptManagerModal,
      openGlobalSettingsModal,
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

<style scoped>
.trmm-agent-menu {
  min-width: 278px;
  max-width: 340px;
  max-height: min(76vh, 610px);
  overflow: hidden;
}

.trmm-am-header {
  flex: 0 0 auto;
  min-height: 36px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-am-header--dark {
  background: rgba(15, 23, 42, 0.65);
}

.trmm-am-header--light {
  background: #f1f5f9;
}

.trmm-am-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.trmm-am-dot--positive {
  background: #22c55e;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.28);
}

.trmm-am-dot--warning {
  background: #f59e0b;
}

.trmm-am-dot--negative {
  background: #ef4444;
}

.trmm-am-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.trmm-am-section-label {
  padding: 5px 12px 3px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
}

body.body--light .trmm-am-section-label {
  color: #64748b;
}

.trmm-am-item {
  min-height: 33px !important;
  margin: 1px 6px;
  padding: 3px 8px !important;
  border-radius: 7px;
  font-size: 12.5px;
  transition: background-color 0.13s ease;
}

.trmm-am-item:hover {
  background: rgba(148, 163, 184, 0.14);
}

.trmm-am-item--danger:hover {
  background: rgba(239, 68, 68, 0.16) !important;
}

.trmm-am-sep {
  opacity: 0.5;
  margin-left: 10px;
  margin-right: 10px;
}

.trmm-am-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.trmm-am-icon--blue {
  background: rgba(59, 130, 246, 0.16);
  color: #60a5fa;
}

.trmm-am-icon--sky {
  background: rgba(14, 165, 233, 0.16);
  color: #38bdf8;
}

.trmm-am-icon--teal {
  background: rgba(20, 184, 166, 0.16);
  color: #2dd4bf;
}

.trmm-am-icon--indigo {
  background: rgba(99, 102, 241, 0.16);
  color: #818cf8;
}

.trmm-am-icon--purple {
  background: rgba(168, 85, 247, 0.16);
  color: #c084fc;
}

.trmm-am-icon--amber {
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
}

.trmm-am-icon--orange {
  background: rgba(249, 115, 22, 0.16);
  color: #fb923c;
}

.trmm-am-icon--emerald {
  background: rgba(34, 197, 94, 0.16);
  color: #4ade80;
}

.trmm-am-icon--red {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
}

.trmm-am-icon--slate {
  background: rgba(148, 163, 184, 0.16);
  color: #cbd5e1;
}

body.body--light .trmm-am-icon--blue { color: #2563eb; }
body.body--light .trmm-am-icon--sky { color: #0284c7; }
body.body--light .trmm-am-icon--teal { color: #0f766e; }
body.body--light .trmm-am-icon--indigo { color: #4f46e5; }
body.body--light .trmm-am-icon--purple { color: #7e22ce; }
body.body--light .trmm-am-icon--amber { color: #b45309; }
body.body--light .trmm-am-icon--orange { color: #c2410c; }
body.body--light .trmm-am-icon--emerald { color: #15803d; }
body.body--light .trmm-am-icon--red { color: #dc2626; }
body.body--light .trmm-am-icon--slate { color: #475569; }
</style>
