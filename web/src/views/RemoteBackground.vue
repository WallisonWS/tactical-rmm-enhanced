<template>
  <div>
    <q-tabs
      v-model="tab"
      dense
      inline-label
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      align="left"
      narrow-indicator
    >
      <q-tab name="terminal" icon="fas fa-terminal" label="Terminal" />
      <q-tab
        name="filebrowser"
        icon="far fa-folder-open"
        label="File Browser"
      />
      <q-tab
        v-if="$route.query.agentPlatform === 'windows'"
        name="services"
        icon="fas fa-cogs"
        label="Services"
      />
      <q-tab name="processes" icon="fas fa-chart-area" label="Processes" />
      <q-tab
        v-if="$route.query.agentPlatform === 'windows'"
        name="eventlog"
        icon="fas fa-clipboard-list"
        label="Event Log"
      />
      <q-tab v-if="$route.query.agentPlatform === 'windows'" name="registry">
        <div class="flex items-center text-weight-bold text-subtitle2">
          <q-icon :name="`img:${registryIcon}`" size="25px" />
          <span class="q-ml-sm font">Registry</span>
        </div>
      </q-tab>
      <q-space />
      <q-badge
        v-if="natsOnline !== null"
        :color="natsOnline ? 'positive' : 'negative'"
        class="q-mr-xs text-caption"
        :label="natsOnline ? 'NATS: Online' : 'NATS: Inacessível'"
      />
      <q-btn
        v-if="natsOnline === false || meshNeedCheck"
        dense
        flat
        size="sm"
        color="warning"
        icon="refresh"
        label="Reconectar"
        no-caps
        class="q-mr-xs"
        @click="reconnectSession"
      />
      <LanguageSwitcher />
    </q-tabs>
    <q-banner
      v-if="diagnosticReason && (natsOnline === false || (usingLegacyMesh && meshConnected === false))"
      dense
      class="bg-negative text-white q-py-xs q-px-md"
    >
      <template v-slot:avatar>
        <q-icon :name="natsOnline ? 'sync_problem' : 'cloud_off'" />
      </template>
      {{ diagnosticReason }}
      <template v-slot:action>
        <q-btn flat dense no-caps label="Testar Novamente" @click="reconnectSession" />
        <q-btn
          v-if="usingLegacyMesh"
          flat
          dense
          no-caps
          label="Recuperar Mesh"
          @click="repairLegacyMesh"
        />
      </template>
    </q-banner>
    <q-separator />
    <q-tab-panels v-show="tab !== 'filebrowser'" v-model="tab">
      <q-tab-panel name="terminal" class="q-pa-none">
        <TerminalManager
          v-if="terminalMode === 'new'"
          :agent_id="agent_id"
          :agentPlatform="$route.query.agentPlatform"
          :terminalDefaults="terminalDefaults"
        />
        <iframe
          v-else-if="terminal"
          :key="`term-${meshFrameKey}`"
          allow="clipboard-read; clipboard-write"
          :src="terminal"
          :style="{
            height: `${$q.screen.height - 30}px`,
            width: `${$q.screen.width}px`,
          }"
        ></iframe>
      </q-tab-panel>
      <q-tab-panel name="processes" class="q-pa-none">
        <ProcessManager :agent_id="agent_id" />
      </q-tab-panel>
      <q-tab-panel
        v-if="$route.query.agentPlatform === 'windows'"
        name="services"
        class="q-pa-none"
      >
        <ServicesManager
          :agent_id="agent_id"
          :agentPlatform="$route.query.agentPlatform"
        />
      </q-tab-panel>
      <q-tab-panel
        v-if="$route.query.agentPlatform === 'windows'"
        name="eventlog"
        class="q-pa-none"
      >
        <EventLogManager
          :agent_id="agent_id"
          :agentPlatform="$route.query.agentPlatform"
        />
      </q-tab-panel>
      <q-tab-panel
        v-if="$route.query.agentPlatform === 'windows'"
        name="registry"
        class="q-pa-none"
      >
        <RegistryManager :agent_id="agent_id" />
      </q-tab-panel>
    </q-tab-panels>
    <FileBrowserManager
      v-if="fileBrowserDefaultsLoaded && fileBrowserMode === 'new'"
      v-show="tab === 'filebrowser'"
      :agent_id="agent_id"
      :agent-platform="String($route.query.agentPlatform || 'windows')"
      :max-upload-file-size-bytes="fileBrowserMaxUploadFileSizeBytes"
    />
    <iframe
      v-if="
        tab === 'filebrowser' &&
        fileBrowserDefaultsLoaded &&
        fileBrowserMode === 'legacy'
      "
      :key="`file-${meshFrameKey}`"
      allow="clipboard-read; clipboard-write"
      :src="file"
      :style="{
        height: `${$q.screen.height - 30}px`,
        width: `${$q.screen.width}px`,
      }"
    ></iframe>
    <div
      v-else-if="tab === 'filebrowser' && !fileBrowserDefaultsLoaded"
      class="file-browser-status"
    >
      <q-spinner color="primary" size="28px" />
    </div>
    <div
      v-else-if="
        tab === 'filebrowser' &&
        (fileBrowserMode === 'denied' || fileBrowserMode === 'error')
      "
      class="file-browser-status"
    >
      <q-icon
        :name="fileBrowserMode === 'denied' ? 'lock' : 'error_outline'"
        size="32px"
        :color="fileBrowserMode === 'denied' ? 'grey' : 'negative'"
      />
      <div class="file-browser-status__label">{{ fileBrowserError }}</div>
      <q-btn
        v-if="fileBrowserMode === 'error'"
        unelevated
        no-caps
        color="primary"
        label="Retry"
        @click="retryFileBrowserDefaults"
      />
    </div>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted, defineAsyncComponent } from "vue";
import { useRoute } from "vue-router";
import { useQuasar, useMeta } from "quasar";
import {
  fetchAgentMeshCentralURLs,
  fetchAgentTerminalDefaults,
  fetchAgentFileBrowserDefaults,
  sendAgentRecoverMesh,
} from "@/api/agents";
import { fetchDashboardInfo } from "@/api/core";
import { notifyError, notifySuccess } from "@/utils/notify";
import { syncDarkModeWithSavedPalette } from "@/utils/themePalettes";

// ui imports
import ProcessManager from "@/components/agents/remotebg/ProcessManager.vue";
import ServicesManager from "@/components/agents/remotebg/ServicesManager.vue";
import EventLogManager from "@/components/agents/remotebg/EventLogManager.vue";
import RegistryManager from "@/components/agents/remotebg/RegistryManager.vue";
import registryIcon from "../assets/windows-registry.png";
import TerminalManager from "@/components/agents/remotebg/TerminalManager.vue";
import LanguageSwitcher from "@/components/LanguageSwitcher.vue";
import { t } from "@/i18n";

const FileBrowserManager = defineAsyncComponent(
  () => import("@/components/agents/remotebg/FileBrowserManager.vue"),
);

export default {
  name: "RemoteBackground",
  components: {
    ServicesManager,
    EventLogManager,
    ProcessManager,
    RegistryManager,
    FileBrowserManager,
    TerminalManager,
    LanguageSwitcher,
  },
  setup() {
    // setup quasar
    const $q = useQuasar();

    // vue router
    const { params } = useRoute();

    // meshcentral tabs
    const terminal = ref("");
    const file = ref("");
    const tab = ref("terminal");
    const terminalMode = ref("legacy");
    const terminalDefaults = ref(null);
    const fileBrowserMode = ref(null);
    const fileBrowserError = ref("");
    const fileBrowserDefaultsLoaded = ref(false);
    const fileBrowserMaxUploadFileSizeBytes = ref(0);
    let fileBrowserDefaultsPromise = null;

    const agent_id = computed(() => params.agent_id);
    const natsOnline = ref(null);
    const meshConnected = ref(null);
    const diagnosticReason = ref("");
    const meshFrameKey = ref(0);
    const usingLegacyMesh = computed(
      () =>
        (tab.value === "terminal" && terminalMode.value === "legacy") ||
        (tab.value === "filebrowser" && fileBrowserMode.value === "legacy"),
    );
    const meshNeedCheck = computed(() => usingLegacyMesh.value && meshConnected.value === false);

    async function getMeshURLs(wake = false) {
      try {
        const data = await fetchAgentMeshCentralURLs(params.agent_id, wake ? { wake: 1 } : { wake: 0 });
        if (!data) return;
        terminal.value = data.terminal;
        file.value = data.file;
        meshFrameKey.value += 1;
        natsOnline.value = typeof data.nats_online === "boolean" ? data.nats_online : null;
        meshConnected.value = typeof data.mesh_connected === "boolean" ? data.mesh_connected : null;
        diagnosticReason.value = data.diagnostic_reason || "";
        useMeta({
          title: `${data.hostname} - ${data.client} - ${data.site} | Remote Background`,
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function reconnectSession() {
      await getMeshURLs(usingLegacyMesh.value);
      await getTerminalDefaults();
      if (tab.value === "filebrowser") {
        retryFileBrowserDefaults();
      }
    }

    async function repairLegacyMesh() {
      $q.loading.show({ message: "Reparando Mesh Agent..." });
      try {
        const msg = await sendAgentRecoverMesh(params.agent_id);
        await getMeshURLs(true);
        notifySuccess(msg);
      } catch (e) {
        notifyError("Falha ao contatar agente via NATS para recuperar Mesh.");
      } finally {
        $q.loading.hide();
      }
    }

    async function getDashInfo() {
      const { dark_mode } = await fetchDashboardInfo();
      syncDarkModeWithSavedPalette(dark_mode);
      $q.loadingBar.setDefaults({ size: "0px" });
    }

    async function getTerminalDefaults() {
      try {
        const data = await fetchAgentTerminalDefaults(params.agent_id);
        terminalDefaults.value = data;

        // TODO remove this after a few releases as all agents should be updated by then
        const wantsNewTerminal = data?.terminal_mode === "new";
        const supportsNewTerminal = data?.supports_new_terminal === true;

        if (wantsNewTerminal && !supportsNewTerminal) {
          terminalMode.value = "legacy";

          $q.notify({
            type: "warning",
            message:
              "New terminal mode requires agent version 2.11.0 or higher. Reverting to legacy terminal mode. Please update the agent to use the new terminal.",
            timeout: 6000,
          });
          return;
        }

        terminalMode.value = wantsNewTerminal ? "new" : "legacy";
      } catch (e) {
        terminalMode.value = "legacy";

        $q.notify({
          type: "negative",
          message:
            e?.response?.data?.detail || "Failed to load terminal settings",
        });
      }
    }

    async function getFileBrowserDefaults() {
      fileBrowserError.value = "";
      try {
        const data = await fetchAgentFileBrowserDefaults(params.agent_id);

        // TODO remove this after a few releases as all agents should be updated by then
        const wantsNewFileBrowser = data?.file_browser_mode === "new";
        const supportsNewFileBrowser = data?.supports_new_file_browser === true;

        if (wantsNewFileBrowser && !supportsNewFileBrowser) {
          fileBrowserMode.value = "legacy";

          $q.notify({
            type: "warning",
            message:
              "New file browser mode requires agent version 2.12.0 or higher. Reverting to legacy file browser mode. Please update the agent to use the new file browser.",
            timeout: 6000,
          });
          return;
        }

        fileBrowserMaxUploadFileSizeBytes.value =
          Number(data?.max_upload_file_size_bytes) || 0;
        fileBrowserMode.value = wantsNewFileBrowser ? "new" : "legacy";
      } catch (e) {
        const status = e?.response?.status;
        if (status === 403) {
          fileBrowserMode.value = "denied";
          fileBrowserError.value =
            "You do not have permission to use the file browser.";
        } else {
          const detail = e?.response?.data?.detail;
          fileBrowserMode.value = "error";
          fileBrowserError.value =
            typeof detail === "string" && detail.trim()
              ? detail
              : "Failed to load file browser settings";
        }

        $q.notify({
          type: "negative",
          message: fileBrowserError.value,
        });
      } finally {
        fileBrowserDefaultsLoaded.value = true;
      }
    }

    function ensureFileBrowserDefaults() {
      if (fileBrowserDefaultsLoaded.value || fileBrowserDefaultsPromise) {
        return fileBrowserDefaultsPromise;
      }
      fileBrowserDefaultsPromise = getFileBrowserDefaults();
      return fileBrowserDefaultsPromise;
    }

    function retryFileBrowserDefaults() {
      fileBrowserDefaultsLoaded.value = false;
      fileBrowserDefaultsPromise = null;
      fileBrowserMode.value = null;
      fileBrowserError.value = "";
      ensureFileBrowserDefaults();
    }

    watch(tab, (name) => {
      if (name === "filebrowser") {
        if (fileBrowserMode.value === "error") {
          retryFileBrowserDefaults();
          return;
        }
        ensureFileBrowserDefaults();
      }
    });

    // When legacy Mesh mode is required, wake & verify Mesh Agent automatically
    watch(usingLegacyMesh, (needsLegacy) => {
      if (needsLegacy && meshConnected.value !== true) {
        getMeshURLs(true);
      }
    });

    // vue lifecycle hooks
    onMounted(() => {
      getDashInfo();
      getMeshURLs(false);
      getTerminalDefaults();
    });

    return {
      // reactive data
      terminal,
      file,
      tab,
      agent_id,
      registryIcon,
      terminalMode,
      terminalDefaults,
      fileBrowserMode,
      fileBrowserError,
      fileBrowserDefaultsLoaded,
      fileBrowserMaxUploadFileSizeBytes,
      retryFileBrowserDefaults,
      natsOnline,
      meshConnected,
      diagnosticReason,
      meshFrameKey,
      usingLegacyMesh,
      meshNeedCheck,
      reconnectSession,
      repairLegacyMesh,
      t,
    };
  },
};
</script>

<style scoped>
.file-browser-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: calc(100vh - 80px);
  padding: 24px;
  text-align: center;
}

.file-browser-status__label {
  max-width: 420px;
  font-size: 0.95rem;
  line-height: 1.4;
  color: rgba(0, 0, 0, 0.7);
}

.body--dark .file-browser-status__label {
  color: rgba(255, 255, 255, 0.7);
}
</style>
