<template>
  <div v-if="!selectedAgent" class="q-pa-md text-grey-6 row items-center q-gutter-x-sm">
    <q-icon name="developer_board" size="20px" />
    <span>Nenhum agente selecionado</span>
  </div>
  <div
    v-else-if="agentPlatform && agentPlatform.toLowerCase() !== 'windows'"
    class="q-pa-md text-grey-6 row items-center q-gutter-x-sm"
  >
    <q-icon name="info_outline" size="20px" color="amber-6" />
    <span>Inventário WMI detalhado disponível apenas para agentes Windows</span>
  </div>
  <div v-else class="trmm-assets-root column no-wrap fit overflow-hidden">
    <!-- Pinned Category Tabs + Quick Search Toolbar -->
    <div
      class="trmm-assets-header"
      :class="$q.dark.isActive ? 'trmm-assets-header--dark' : 'trmm-assets-header--light'"
    >
      <q-tabs
        v-model="tab"
        dense
        inline-label
        mobile-arrows
        outside-arrows
        class="trmm-assets-tabs"
        :class="$q.dark.isActive ? 'text-grey-5' : 'text-grey-7'"
        active-color="primary"
        indicator-color="primary"
        align="left"
        narrow-indicator
        no-caps
      >
        <q-tab
          v-for="cat in categories"
          :key="cat.name"
          :name="cat.name"
          :icon="cat.icon"
          :label="cat.label"
          class="trmm-assets-tab"
        />
      </q-tabs>

      <div class="trmm-assets-toolbar row items-center q-px-md q-py-xs q-gutter-x-sm">
        <q-input
          v-model="wmiSearch"
          dense
          outlined
          clearable
          placeholder="Filtrar campo ou valor WMI..."
          class="trmm-assets-search"
        >
          <template v-slot:prepend>
            <q-icon name="search" size="16px" color="primary" />
          </template>
        </q-input>

        <q-toggle
          v-model="hideEmpty"
          dense
          size="sm"
          color="primary"
          label="Ocultar vazios"
          class="text-caption"
        />

        <q-space />

        <q-btn
          dense
          flat
          no-caps
          size="sm"
          icon="refresh"
          color="primary"
          label="Recarregar"
          :loading="loading"
          class="q-px-sm"
          @click="getWMIData"
        >
          <q-tooltip>Recarregar propriedades WMI do equipamento</q-tooltip>
        </q-btn>
      </div>
    </div>

    <!-- Single-Layer Scrollable Body (Native Mouse Wheel Scroll) -->
    <div class="col trmm-panel-scroll q-pa-md" style="min-height: 0">
      <div v-if="loading" class="flex flex-center q-pa-lg">
        <q-spinner-dots size="36px" color="primary" />
      </div>
      <WmiDetail
        v-else
        :info="currentCategoryData"
        :search="wmiSearch"
        :hide-empty="hideEmpty"
        :category-label="currentCategoryLabel"
      />
    </div>
  </div>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { fetchAgent } from "@/api/agents";

// ui imports
import WmiDetail from "@/components/agents/WmiDetail.vue";

const WMI_CATEGORIES = [
  { name: "os", label: "Sistema Operacional", icon: "desktop_windows" },
  { name: "cpu", label: "CPU", icon: "memory" },
  { name: "mem", label: "Memória", icon: "developer_board" },
  { name: "disk", label: "Discos", icon: "storage" },
  { name: "network_config", label: "Rede (IP/DNS)", icon: "lan" },
  { name: "network_adapter", label: "Adaptadores", icon: "settings_ethernet" },
  { name: "graphics", label: "Vídeo / GPU", icon: "tv" },
  { name: "desktop_monitor", label: "Monitores", icon: "monitor" },
  { name: "bios", label: "BIOS", icon: "settings_input_component" },
  { name: "base_board", label: "Placa-Mãe", icon: "dashboard_customize" },
  { name: "comp_sys", label: "Sistema", icon: "computer" },
  { name: "comp_sys_prod", label: "Produto", icon: "inventory_2" },
  { name: "usb", label: "USB", icon: "usb" },
];

export default {
  name: "AssetsTab",
  components: { WmiDetail },
  setup() {
    const store = useStore();
    const selectedAgent = computed(() => store.state.selectedRow);
    const agentPlatform = computed(() => store.state.agentPlatform);
    const loading = ref(false);

    const assets = ref({});
    const tab = ref("os");
    const wmiSearch = ref("");
    const hideEmpty = ref(true);

    const currentCategoryData = computed(() => assets.value?.[tab.value] || []);
    const currentCategoryLabel = computed(
      () => WMI_CATEGORIES.find((c) => c.name === tab.value)?.label || "",
    );

    async function getWMIData() {
      if (!selectedAgent.value) return;
      loading.value = true;
      try {
        const { wmi_detail } = await fetchAgent(selectedAgent.value);
        assets.value = wmi_detail || {};
      } catch (e) {
        console.error(e);
        assets.value = {};
      } finally {
        loading.value = false;
      }
    }

    watch(selectedAgent, (newValue) => {
      if (newValue) {
        getWMIData();
      } else {
        assets.value = {};
      }
    });

    onMounted(() => {
      if (selectedAgent.value) getWMIData();
    });

    return {
      categories: WMI_CATEGORIES,
      assets,
      tab,
      wmiSearch,
      hideEmpty,
      loading,
      selectedAgent,
      agentPlatform,
      currentCategoryData,
      currentCategoryLabel,
      getWMIData,
    };
  },
};
</script>

<style scoped>
.trmm-assets-header {
  flex: 0 0 auto;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-assets-header--dark {
  background: rgba(15, 23, 42, 0.28);
}

.trmm-assets-header--light {
  background: rgba(248, 250, 252, 0.92);
}

.trmm-assets-tabs {
  padding: 2px 8px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}

.trmm-assets-tab {
  min-height: 32px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 6px 6px 0 0;
}

.trmm-assets-tabs :deep(.q-tab__icon) {
  font-size: 15px;
  margin-right: 5px;
}

.trmm-assets-tabs :deep(.q-tab--active) {
  background: rgba(25, 118, 210, 0.12);
  font-weight: 600;
}

.trmm-assets-toolbar {
  min-height: 38px;
}

.trmm-assets-search {
  width: 260px;
  max-width: 55vw;
}

.trmm-assets-search :deep(.q-field__control) {
  height: 28px;
  min-height: 28px;
  border-radius: 7px;
  font-size: 12px;
}

.trmm-assets-search :deep(.q-field__marginal) {
  height: 28px;
}
</style>
