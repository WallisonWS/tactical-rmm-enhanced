<template>
  <div class="trmm-subtabs">
    <div
      class="trmm-subtabs-header"
      :class="$q.dark.isActive ? 'trmm-subtabs-header--dark' : 'trmm-subtabs-header--light'"
    >
      <q-tabs
        v-model="subtab"
        dense
        inline-label
        mobile-arrows
        outside-arrows
        class="trmm-subtabs-bar"
        :class="$q.dark.isActive ? 'text-grey-5' : 'text-grey-7'"
        active-color="primary"
        indicator-color="primary"
        align="left"
        narrow-indicator
        no-caps
      >
        <q-tab
          v-if="activeTabs.includes('summary')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="summary"
          icon="space_dashboard"
          :label="t('tabs.summary')"
        />
        <q-tab
          v-if="activeTabs.includes('checks')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="checks"
          icon="task_alt"
          :label="t('tabs.checks')"
        />
        <q-tab
          v-if="activeTabs.includes('tasks')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="tasks"
          icon="auto_mode"
          :label="t('tabs.tasks')"
        />
        <q-tab
          v-if="activeTabs.includes('patches')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="patches"
          icon="system_update_alt"
          :label="t('tabs.patches')"
        />
        <q-tab
          v-if="activeTabs.includes('software')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="software"
          icon="apps"
          :label="t('tabs.software')"
        />
        <q-tab
          v-if="activeTabs.includes('history')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="history"
          icon="history"
          :label="t('tabs.history')"
        />
        <q-tab
          v-if="activeTabs.includes('notes')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="notes"
          icon="sticky_note_2"
          :label="t('tabs.notes')"
        />
        <q-tab
          v-if="activeTabs.includes('assets')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="assets"
          icon="developer_board"
          :label="t('tabs.assets')"
        />
        <q-tab
          v-if="activeTabs.includes('debug')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="debug"
          icon="bug_report"
          :label="t('tabs.debug')"
        />
        <q-tab
          v-if="activeTabs.includes('audit')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="audit"
          icon="manage_search"
          :label="t('tabs.audit')"
        />
        <q-tab
          v-if="activeTabs.includes('telemetry')"
          content-class="min-width"
          class="trmm-subtab-item"
          name="telemetry"
          icon="speed"
          :label="t('tabs.telemetry')"
        />
      </q-tabs>
    </div>

    <div class="trmm-subtabs-body">
      <q-tab-panels
        v-model="subtab"
        :animated="false"
        class="fit bg-transparent trmm-subtab-panels"
      >
        <q-tab-panel
          v-if="activeTabs.includes('summary')"
          name="summary"
          class="q-pa-none trmm-panel-scroll"
        >
          <SummaryTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('checks')"
          name="checks"
          class="q-pa-none trmm-panel-scroll"
        >
          <ChecksTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('tasks')"
          name="tasks"
          class="q-pa-none trmm-panel-scroll"
        >
          <AutomatedTasksTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('patches')"
          name="patches"
          class="q-pa-none trmm-panel-scroll"
        >
          <WinUpdateTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('software')"
          name="software"
          class="q-pa-none trmm-panel-scroll"
        >
          <SoftwareTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('history')"
          name="history"
          class="q-pa-none trmm-panel-scroll"
        >
          <HistoryTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('notes')"
          name="notes"
          class="q-pa-none trmm-panel-scroll"
        >
          <NotesTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('assets')"
          name="assets"
          class="q-pa-none fit overflow-hidden"
        >
          <AssetsTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('debug')"
          name="debug"
          class="q-pa-none trmm-panel-scroll"
        >
          <DebugTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('audit')"
          name="audit"
          class="q-pa-none trmm-panel-scroll"
        >
          <AuditTab />
        </q-tab-panel>
        <q-tab-panel
          v-if="activeTabs.includes('telemetry')"
          name="telemetry"
          class="q-pa-none trmm-panel-scroll"
        >
          <TelemetryTab />
        </q-tab-panel>
      </q-tab-panels>
    </div>
  </div>
</template>

<script>
// composition imports
import { ref } from "vue";
import { t } from "@/i18n";

// ui imports
import SummaryTab from "@/components/agents/SummaryTab.vue";
import ChecksTab from "@/components/agents/ChecksTab.vue";
import AutomatedTasksTab from "@/components/agents/AutomatedTasksTab.vue";
import WinUpdateTab from "@/components/agents/WinUpdateTab.vue";
import SoftwareTab from "@/components/agents/SoftwareTab.vue";
import HistoryTab from "@/components/agents/HistoryTab.vue";
import AuditTab from "@/components/agents/AuditTab.vue";
import DebugTab from "@/components/agents/DebugTab.vue";
import AssetsTab from "@/components/agents/AssetsTab.vue";
import NotesTab from "@/components/agents/NotesTab.vue";
import TelemetryTab from "@/components/agents/TelemetryTab.vue";

export default {
  name: "SubTableTabs",
  components: {
    SummaryTab,
    ChecksTab,
    AutomatedTasksTab,
    WinUpdateTab,
    SoftwareTab,
    HistoryTab,
    AuditTab,
    DebugTab,
    AssetsTab,
    NotesTab,
    TelemetryTab,
  },
  props: {
    activeTabs: {
      type: Array,
      default: () => [
        "summary",
        "checks",
        "tasks",
        "patches",
        "software",
        "history",
        "notes",
        "assets",
        "debug",
        "audit",
        "telemetry",
      ],
    },
  },
  setup(props) {
    return {
      subtab: ref(props.activeTabs[0]),
      t,
    };
  },
};
</script>

<style scoped>
.trmm-subtabs-header {
  flex: 0 0 auto;
  padding: 2px 6px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.trmm-subtabs-header--dark {
  background: rgba(15, 23, 42, 0.42);
}

.trmm-subtabs-header--light {
  background: rgba(241, 245, 249, 0.85);
}

.trmm-subtabs-bar :deep(.q-tab) {
  min-height: 36px;
  padding: 0 11px;
  border-radius: 7px 7px 0 0;
  font-size: 12.5px;
  font-weight: 500;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.trmm-subtabs-bar :deep(.q-tab:hover) {
  background: rgba(148, 163, 184, 0.1);
}

.trmm-subtabs-bar :deep(.q-tab--active) {
  font-weight: 600;
  background: rgba(25, 118, 210, 0.12);
}

.trmm-subtabs-bar :deep(.q-tab__icon) {
  font-size: 17px;
  margin-right: 5px;
}
</style>
