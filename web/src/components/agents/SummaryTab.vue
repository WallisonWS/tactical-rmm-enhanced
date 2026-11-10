<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else-if="!summary && loading" class="q-pa-md flex flex-center">
    <q-circular-progress
      indeterminate
      size="50px"
      color="primary"
      class="q-ma-md"
    />
  </div>
  <div v-else-if="summary" class="q-pa-sm">
    <q-bar dense style="background-color: transparent">
      <q-btn
        dense
        flat
        size="md"
        class="q-mr-sm"
        icon="refresh"
        @click="refreshSummary"
      />
      <q-icon
        v-if="summary.status === 'overdue'"
        name="fas fa-signal"
        size="1.2em"
        :color="dash_negative_color"
        class="q-mr-sm"
      >
        <q-tooltip>Agent overdue</q-tooltip>
      </q-icon>
      <q-icon
        v-else-if="summary.status === 'offline'"
        name="fas fa-signal"
        size="1.2em"
        :color="dash_warning_color"
        class="q-mr-sm"
      >
        <q-tooltip>{{ store.getters.formatDate(summary.last_seen) }}</q-tooltip>
      </q-icon>
      <q-icon
        v-else
        name="fas fa-signal"
        size="1.2em"
        :color="dash_positive_color"
        class="q-mr-sm"
      >
        <q-tooltip>{{ store.getters.formatDate(summary.last_seen) }}</q-tooltip>
      </q-icon>
      <b>{{ summary.hostname }}</b>
      <span v-if="summary.maintenance_mode">
        &bull; <q-badge color="green"> Maintenance Mode </q-badge>
      </span>
      &bull; {{ summary.operating_system }} &bull; Agent v{{ summary.version }}
      <q-space />
      <q-btn
        dense
        unelevated
        color="primary"
        label="Take Control"
        icon="computer"
        size="sm"
        no-caps
        class="q-mr-sm q-px-sm"
        @click="runTakeControl(selectedAgent)"
      />
      <q-btn
        dense
        flat
        label="Remote Background"
        icon="terminal"
        size="md"
        no-caps
        class="q-mr-sm"
        @click="runRemoteBackground(selectedAgent, summary.plat)"
      />
      <q-btn
        v-if="summary.plat === 'windows'"
        dense
        flat
        label="Conectar RDP (.rdp)"
        icon="desktop_windows"
        size="md"
        no-caps
        class="q-mr-sm"
        :loading="rdpConnecting"
        @click="connectNativeRDP"
      />
      <q-btn
        v-if="summary.plat === 'windows' && !adDomainInfo.inDomain"
        dense
        unelevated
        color="amber-9"
        label="Ingressar no AD"
        icon="domain_add"
        size="sm"
        no-caps
        class="q-mr-sm q-px-sm"
        @click="showJoinAdDialog = true"
      />
      <q-btn
        dense
        flat
        label="Popout"
        icon="open_in_new"
        size="md"
        no-caps
        class="q-mr-sm"
        @click="openAgentWindow(selectedAgent)"
      />
      <q-btn-dropdown dense flat size="md" no-caps label="Actions">
        <AgentActionMenu :agent="summary" />
      </q-btn-dropdown>
    </q-bar>
    <q-separator class="q-mt-sm" />
    <div class="row">
      <div class="col-4">
        <!-- left -->
        <span class="text-subtitle2 text-bold">Hardware Details</span>
        <q-list dense>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-desktop" />
            </q-item-section>
            <q-item-section>{{ summary.make_model }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-microchip" />
            </q-item-section>
            <q-item-section>{{ cpu }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-memory" />
            </q-item-section>
            <q-item-section>{{ summary.total_ram }} GB RAM</q-item-section>
          </q-item>

          <!-- physical disks -->
          <q-item v-for="(disk, i) in summary.physical_disks" :key="disk + i">
            <q-item-section avatar>
              <q-icon name="far fa-hdd" />
            </q-item-section>
            <q-item-section>{{ disk }}</q-item-section>
          </q-item>
          <!-- graphics -->
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-tv" />
            </q-item-section>
            <q-item-section>{{ summary.graphics }}</q-item-section>
          </q-item>
          <!-- serial -->
          <q-item v-if="serial_number">
            <q-item-section avatar>
              <q-icon name="fa-solid fa-barcode" />
            </q-item-section>
            <q-item-section>{{ serial_number }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-globe-americas" />
            </q-item-section>
            <q-item-section>Public IP: {{ summary.public_ip }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="fas fa-network-wired" />
            </q-item-section>
            <q-item-section>LAN IP: {{ summary.local_ips }}</q-item-section>
          </q-item>
          <q-item v-if="summary.plat === 'windows'">
            <q-item-section avatar>
              <q-icon :name="adDomainInfo.inDomain ? 'domain' : 'domain_disabled'" />
            </q-item-section>
            <q-item-section>
              <div class="row items-center q-gutter-x-xs">
                <span v-if="adDomainInfo.inDomain">
                  Domínio AD: <b>{{ adDomainInfo.domainName }}</b>
                </span>
                <span v-else class="text-warning">
                  Fora do AD ({{ adDomainInfo.domainName }})
                </span>
                <q-btn
                  v-if="!adDomainInfo.inDomain"
                  dense
                  flat
                  size="xs"
                  color="amber-8"
                  icon="domain_add"
                  label="Ingressar no AD"
                  no-caps
                  @click="showJoinAdDialog = true"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </div>
      <div class="col-2">
        <span class="text-subtitle2 text-bold">Checks Status</span>
        <br />
        <div v-if="summary.checks.total !== 0">
          <q-chip v-if="summary.checks.passing" square size="lg">
            <q-avatar
              size="lg"
              square
              icon="done"
              :color="dash_positive_color"
              text-color="white"
            />
            <small>{{ summary.checks.passing }} checks passing</small>
          </q-chip>
          <q-chip v-if="summary.checks.failing" square size="lg">
            <q-avatar
              size="lg"
              square
              icon="cancel"
              :color="dash_negative_color"
              text-color="white"
            />
            <small>{{ summary.checks.failing }} checks failing</small>
          </q-chip>
          <q-chip v-if="summary.checks.warning" square size="lg">
            <q-avatar
              size="lg"
              square
              icon="warning"
              :color="dash_warning_color"
              text-color="white"
            />
            <small>{{ summary.checks.warning }} checks warning</small>
          </q-chip>
          <q-chip v-if="summary.checks.info" square size="lg">
            <q-avatar
              size="lg"
              square
              icon="info"
              :color="dash_info_color"
              text-color="white"
            />
            <small>{{ summary.checks.info }} checks info</small>
          </q-chip>
          <span
            v-if="
              summary.checks.total !== 0 &&
              summary.checks.passing === 0 &&
              summary.checks.failing === 0 &&
              summary.checks.warning === 0 &&
              summary.checks.info === 0
            "
            >{{ summary.checks.total }} checks awaiting first
            synchronization</span
          >
        </div>
        <div v-else>No checks</div>

        <span
          v-if="customFields.length > 0"
          class="text-subtitle2 text-bold block q-mt-xl"
          >Custom Fields</span
        >
        <q-list dense>
          <q-item v-for="(field, i) in customFields" :key="field + i">
            <q-item-section thumbnail>
              <q-icon name="fas fa-user" size="xs" />
            </q-item-section>
            <q-item-section>{{ field.name }}: {{ field.value }}</q-item-section>
          </q-item>
        </q-list>
      </div>
      <div class="col-1"></div>
      <!-- right -->
      <div class="col-3">
        <span class="text-subtitle2 text-bold">Disks</span>
        <div v-for="disk in disks" :key="disk.device">
          <span>{{ disk.device }} ({{ disk.fstype }})</span>
          <q-linear-progress
            rounded
            size="15px"
            :value="disk.percent / 100"
            :color="diskBarColor(disk.percent)"
            class="q-mt-sm"
          />
          <span>{{ disk.free }} free of {{ disk.total }}</span>
          <q-separator />
        </div>
      </div>
      <div class="col-2"></div>
    </div>

    <!-- Modal: Ingressar Computador no Domínio Active Directory -->
    <q-dialog v-model="showJoinAdDialog" persistent>
      <q-card style="min-width: 440px">
        <q-card-section class="row items-center">
          <q-icon name="domain_add" color="primary" size="sm" class="q-mr-sm" />
          <div class="text-subtitle1 text-weight-bold">
            Ingressar {{ summary.hostname }} no Active Directory
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-y-sm">
          <q-input
            v-model="joinAdForm.domain_name"
            dense
            outlined
            label="Domínio Active Directory (ex: crd.med.br)"
          />
          <q-input
            v-model="joinAdForm.admin_user"
            dense
            outlined
            label="Usuário Administrador do Domínio (ex: CRD\administrador)"
          />
          <q-input
            v-model="joinAdForm.admin_password"
            type="password"
            dense
            outlined
            label="Senha do Administrador do Domínio"
          />
          <q-input
            v-model="joinAdForm.ou_path"
            dense
            outlined
            label="Caminho da OU (Opcional — ex: OU=Computadores,DC=crd,DC=med,DC=br)"
          />
          <q-checkbox
            v-model="joinAdForm.restart"
            dense
            label="Reiniciar o computador automaticamente após ingressar no AD"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="primary"
            icon="domain_add"
            label="Ingressar no Domínio"
            :loading="joinAdLoading"
            @click="submitJoinAd"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-inner-loading :showing="loading" color="primary" />
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import {
  fetchAgent,
  refreshAgentWMI,
  runTakeControl,
  runRemoteBackground,
  openAgentWindow,
} from "@/api/agents";
import {
  manageAgentRDP,
  downloadNativeRDPFile,
  joinAgentToADDomain,
  fetchFleetExecutiveSummary,
  fleetDomainMap,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";
import { fetchCustomFields } from "@/api/core";

// ui imports
import AgentActionMenu from "@/components/agents/AgentActionMenu.vue";

export default {
  name: "SummaryTab",
  components: {
    AgentActionMenu,
  },
  setup() {
    // vuex setup
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const refreshSummaryTab = computed(() => store.state.refreshSummaryTab);
    const dash_info_color = computed(() => store.state.dash_info_color);
    const dash_positive_color = computed(() => store.state.dash_positive_color);
    const dash_negative_color = computed(() => store.state.dash_negative_color);
    const dash_warning_color = computed(() => store.state.dash_warning_color);

    // summary tab logic
    const summary = ref(null);
    const customFieldsDefinitions = ref(null);
    const loading = ref(false);
    const rdpConnecting = ref(false);
    const showJoinAdDialog = ref(false);
    const joinAdLoading = ref(false);
    const joinAdForm = ref({
      domain_name: "",
      admin_user: "",
      admin_password: "",
      ou_path: "",
      restart: false,
    });

    const adDomainInfo = computed(() => {
      const mapEntry = (fleetDomainMap.value || {})[selectedAgent.value];
      if (mapEntry) {
        return {
          inDomain: !!mapEntry.part_of_domain,
          domainName: mapEntry.domain || (mapEntry.part_of_domain ? "AD" : "WORKGROUP"),
        };
      }
      const compSys = summary.value?.wmi_detail?.comp_sys?.[0] || [];
      let partOfDomain = false;
      let domain = "";
      let workgroup = "WORKGROUP";
      if (Array.isArray(compSys)) {
        for (const item of compSys) {
          if (item && typeof item === "object") {
            if ("PartOfDomain" in item) partOfDomain = !!item.PartOfDomain;
            if ("Domain" in item && item.Domain) domain = String(item.Domain);
            if ("Workgroup" in item && item.Workgroup) workgroup = String(item.Workgroup);
          }
        }
      }
      return {
        inDomain: partOfDomain,
        domainName: partOfDomain ? domain || "AD" : domain || workgroup,
      };
    });

    async function connectNativeRDP() {
      if (!summary.value) return;
      rdpConnecting.value = true;
      try {
        await manageAgentRDP(selectedAgent.value, "enable_rdp", false);
      } catch (e) {
        // Proceed to download .rdp file even if remote command was skipped
      } finally {
        rdpConnecting.value = false;
      }
      const rawIps = String(summary.value.local_ips || "");
      const firstIp =
        rawIps
          .split(",")[0]
          .split("/")[0]
          .trim() || summary.value.hostname;
      downloadNativeRDPFile(summary.value.hostname, firstIp, 3389);
      notifySuccess(`Conexão RDP (${firstIp}) habilitada e arquivo ${summary.value.hostname}.rdp baixado!`);
    }

    async function submitJoinAd() {
      if (
        !joinAdForm.value.domain_name.trim() ||
        !joinAdForm.value.admin_user.trim() ||
        !joinAdForm.value.admin_password
      ) {
        notifyError("Preencha o Domínio AD, Usuário Administrador e Senha.");
        return;
      }
      joinAdLoading.value = true;
      try {
        const res = await joinAgentToADDomain(selectedAgent.value, {
          domain: joinAdForm.value.domain_name.trim(),
          username: joinAdForm.value.admin_user.trim(),
          password: joinAdForm.value.admin_password,
          ou_path: joinAdForm.value.ou_path.trim(),
          restart: joinAdForm.value.restart,
        });
        if (res?.success) {
          notifySuccess(res.output || `${summary.value.hostname} ingressado no domínio AD com sucesso!`);
          showJoinAdDialog.value = false;
          joinAdForm.value.admin_password = "";
          await fetchFleetExecutiveSummary().catch(() => {});
          await refreshSummary();
        } else {
          notifyError(res?.output || "Falha ao ingressar no domínio AD.");
        }
      } catch (e) {
        notifyError(e?.response?.data?.error || "Erro ao ingressar o computador no domínio AD.");
      } finally {
        joinAdLoading.value = false;
      }
    }

    const serial_number = computed(() => {
      if (summary.value.plat === "windows") {
        return summary.value.wmi_detail.bios?.[0]?.[0]?.SerialNumber;
      } else {
        return summary.value.wmi_detail.serialnumber;
      }
    });

    const cpu = computed(() => {
      if (summary.value.cpu_model?.length > 1) {
        return `${summary.value.cpu_model.length}x ${summary.value.cpu_model[0]}`;
      }
      return summary.value.cpu_model[0];
    });

    function diskBarColor(percent) {
      if (percent < 80) {
        return dash_positive_color.value;
      } else if (percent >= 80 && percent < 95) {
        return dash_warning_color.value;
      } else {
        return dash_negative_color.value;
      }
    }

    const disks = computed(() => {
      if (!summary.value.disks) {
        return [];
      }
      const seen = new Set();
      return summary.value.disks.filter((disk) => {
        if (seen.has(disk.device)) return false;
        seen.add(disk.device);
        return true;
      });
    });

    const customFields = computed(() => {
      if (!summary.value.custom_fields) {
        return [];
      }
      if (!customFieldsDefinitions.value) {
        return [];
      }
      const ret = [];
      for (const customField of summary.value.custom_fields) {
        const definition = customFieldsDefinitions.value.find(
          (def) => def.id === customField.field,
        );
        if (
          definition &&
          !definition.hide_in_summary &&
          customField.value?.length > 0
        ) {
          ret.push({
            name: definition.name,
            value: customField.value,
          });
        }
      }

      return ret;
    });

    async function getSummary() {
      loading.value = true;
      summary.value = await fetchAgent(selectedAgent.value);
      customFieldsDefinitions.value = await fetchCustomFields();
      store.commit("setRefreshSummaryTab", false);
      store.commit("setAgentPlatform", summary.value.plat);
      loading.value = false;
    }

    async function refreshSummary() {
      loading.value = true;
      summary.value = await fetchAgent(selectedAgent.value);
      try {
        const result = await refreshAgentWMI(selectedAgent.value);
        await getSummary();
        notifySuccess(result);
      } catch (e) {
        console.error(e);
      }
      loading.value = false;
    }

    watch(selectedAgent, (newValue) => {
      if (newValue) {
        getSummary();
      }
    });

    watch(refreshSummaryTab, (newValue) => {
      if (newValue && selectedAgent.value) {
        getSummary();
      }

      store.commit("setRefreshSummaryTab", false);
    });

    onMounted(() => {
      if (selectedAgent.value) getSummary();
    });

    return {
      // reactive data
      summary,
      customFields,
      loading,
      selectedAgent,
      disks,
      dash_info_color,
      dash_positive_color,
      dash_warning_color,
      dash_negative_color,
      serial_number,
      cpu,
      store,
      rdpConnecting,
      showJoinAdDialog,
      joinAdLoading,
      joinAdForm,
      adDomainInfo,

      // methods
      getSummary,
      refreshSummary,
      diskBarColor,
      runTakeControl,
      runRemoteBackground,
      openAgentWindow,
      connectNativeRDP,
      submitJoinAd,
    };
  },
};
</script>
