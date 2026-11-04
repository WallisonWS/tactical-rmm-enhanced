<template>
  <q-page>
    <FileBar />
    <ExecutiveKPIBar v-if="showKpiBar" />
    <q-splitter
      v-model="clientTreeSplitter"
      :limits="[0, 40]"
      :style="{ height: `${$q.screen.height - 50 - (showKpiBar ? 132 : 38)}px` }"
    >
      <template v-slot:before>
        <div
          v-if="!treeReady"
          class="q-pa-sm q-gutter-sm text-center"
          style="height: 30vh"
        >
          <q-spinner size="40px" color="primary" />
        </div>
        <div
          v-else
          class="q-pa-sm q-gutter-sm scroll"
          style="height: 85vh; overflow: initial"
        >
          <q-list dense class="rounded-borders">
            <q-item
              clickable
              v-ripple
              :active="allClientsActive"
              @click="clearTreeSelected"
            >
              <q-item-section avatar>
                <q-icon name="fas fa-home" />
              </q-item-section>
              <q-item-section>{{ t("nav.allClients") }}</q-item-section>
            </q-item>
            <q-tree
              ref="tree"
              :nodes="clientsTree"
              node-key="raw"
              no-nodes-label="No Clients"
              selected-color="primary"
              v-model:selected="selectedTree"
              @update:selected="$store.dispatch('refreshDashboard')"
            >
              <template v-slot:default-header="props">
                <div class="row items-center">
                  <q-icon
                    :name="props.node.icon"
                    :color="props.node.color"
                    class="q-mr-sm"
                  />
                  <div>
                    {{ props.node.label }}
                    <q-tooltip :delay="600">
                      ID: {{ props.node.id }}<br />
                      Agent Count:
                      {{
                        props.node.children
                          ? props.node.client.agent_count
                          : props.node.site.agent_count
                      }}
                    </q-tooltip>
                  </div>

                  <q-menu context-menu>
                    <q-list dense style="min-width: 200px">
                      <q-item
                        clickable
                        v-close-popup
                        @click="showEditModal(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="edit" />
                        </q-item-section>
                        <q-item-section>Edit</q-item-section>
                      </q-item>
                      <q-item
                        clickable
                        v-close-popup
                        @click="showDeleteModal(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="delete" />
                        </q-item-section>
                        <q-item-section>Delete</q-item-section>
                      </q-item>

                      <q-separator></q-separator>

                      <q-item
                        v-if="props.node.children"
                        clickable
                        v-close-popup
                        @click="showAddSiteModal(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="add" />
                        </q-item-section>
                        <q-item-section>Add Site</q-item-section>
                      </q-item>

                      <q-item
                        clickable
                        v-close-popup
                        @click="showToggleMaintenance(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="construction" />
                        </q-item-section>
                        <q-item-section>{{
                          props.node.color === "green"
                            ? "Disable Maintenance Mode"
                            : "Enable Maintenance Mode"
                        }}</q-item-section>
                      </q-item>

                      <q-item
                        v-if="props.node.children === undefined"
                        clickable
                        v-close-popup
                        @click="showInstallAgent(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="cloud_download" />
                        </q-item-section>
                        <q-item-section>Install Agent</q-item-section>
                      </q-item>

                      <q-item
                        clickable
                        v-close-popup
                        @click="showPolicyAdd(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="policy" />
                        </q-item-section>
                        <q-item-section
                          >Assign Automation Policy</q-item-section
                        >
                      </q-item>

                      <q-item
                        clickable
                        v-close-popup
                        @click="showAlertTemplateAdd(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="error" />
                        </q-item-section>
                        <q-item-section>Assign Alert Template</q-item-section>
                      </q-item>

                      <q-item clickable v-ripple @click="getURLActions">
                        <q-item-section side>
                          <q-icon name="open_in_new" />
                        </q-item-section>
                        <q-item-section>Run URL Action</q-item-section>
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
                                runURLAction(
                                  props.node.id,
                                  action.id,
                                  props.node.children ? 'client' : 'site',
                                )
                              "
                            >
                              {{ action.name }}
                            </q-item>
                          </q-list>
                        </q-menu>
                      </q-item>

                      <!-- Bulk Run Checks -->
                      <q-item
                        clickable
                        v-close-popup
                        @click="runChecks(props.node)"
                      >
                        <q-item-section side>
                          <q-icon name="fas fa-check-double" />
                        </q-item-section>
                        <q-item-section>Run Checks</q-item-section>
                      </q-item>

                      <q-item
                        clickable
                        v-if="
                          (props.node.children &&
                            $integrations?.clientMenuIntegrations?.length >
                              0) ||
                          (!props.node.children &&
                            $integrations?.siteMenuIntegrations.length > 0)
                        "
                      >
                        <q-item-section side>
                          <q-icon name="analytics" />
                        </q-item-section>
                        <q-item-section>Reporting</q-item-section>
                        <q-item-section side>
                          <q-icon name="keyboard_arrow_right" />
                        </q-item-section>
                        <integrations-context-menu
                          :type="props.node.children ? 'client' : 'site'"
                          :id="props.node.id"
                        />
                      </q-item>

                      <q-separator></q-separator>

                      <q-item clickable v-close-popup>
                        <q-item-section>Close</q-item-section>
                      </q-item>
                    </q-list>
                  </q-menu>
                </div>
              </template>
            </q-tree>
          </q-list>
        </div>
      </template>

      <template v-slot:after>
        <q-splitter
          v-model="innerModel"
          reverse
          unit="px"
          horizontal
          @update:model-value="$store.commit('SET_SPLITTER', innerModel)"
          after-class="hide-scrollbar"
          before-class="hide-scrollbar"
          emit-immediately
        >
          <template v-slot:before>
            <div class="row items-center no-wrap q-px-xs q-py-xs q-gutter-x-xs">
              <!-- Sidebar Toggle Button -->
              <q-btn
                dense
                flat
                round
                size="sm"
                :icon="clientTreeSplitter > 2 ? 'menu_open' : 'menu'"
                color="primary"
                @click="toggleClientSidebar"
              >
                <q-tooltip>{{ t("dash.toggleSidebar") }}</q-tooltip>
              </q-btn>

              <q-tabs
                v-model="tab"
                dense
                no-caps
                inline-label
                class="text-grey"
                active-color="primary"
                indicator-color="primary"
                align="left"
                narrow-indicator
              >
                <q-tab name="server" icon="fas fa-server" :label="t('nav.servers')" />
                <q-tab
                  name="workstation"
                  icon="computer"
                  :label="t('nav.workstations')"
                />
                <q-tab name="mixed" :label="t('dash.mixed')" />
              </q-tabs>

              <!-- 1-Click Quick Filter Chips -->
              <div class="row items-center no-wrap q-gutter-x-xs gt-xs">
                <q-chip
                  clickable
                  dense
                  size="sm"
                  :outline="search !== ''"
                  color="primary"
                  text-color="white"
                  @click="clearFilter"
                >
                  {{ t("dash.quickAll") }} ({{ filteredAgents.length }})
                </q-chip>
                <q-chip
                  clickable
                  dense
                  size="sm"
                  :outline="!search.includes('is:online')"
                  color="positive"
                  text-color="white"
                  icon="check_circle"
                  @click="setQuickFilter('is:online')"
                >
                  {{ t("dash.quickOnline") }} ({{ onlineCount }})
                </q-chip>
                <q-chip
                  v-if="offlineOrOverdueCount > 0"
                  clickable
                  dense
                  size="sm"
                  :outline="!search.includes('is:offline') && !search.includes('is:overdue')"
                  color="warning"
                  text-color="black"
                  icon="power_off"
                  @click="setQuickFilter('is:offline')"
                >
                  {{ t("dash.quickOffline") }} ({{ offlineOrOverdueCount }})
                </q-chip>
                <q-chip
                  v-if="failingChecksCount > 0"
                  clickable
                  dense
                  size="sm"
                  :outline="!search.includes('is:checksfailing')"
                  color="negative"
                  text-color="white"
                  icon="warning"
                  @click="setQuickFilter('is:checksfailing')"
                >
                  {{ t("dash.quickFailing") }} ({{ failingChecksCount }})
                </q-chip>
                <q-chip
                  v-if="patchesPendingCount > 0"
                  clickable
                  dense
                  size="sm"
                  :outline="!search.includes('is:patchespending')"
                  color="info"
                  text-color="white"
                  icon="system_update"
                  @click="setQuickFilter('is:patchespending')"
                >
                  {{ t("dash.quickPatches") }} ({{ patchesPendingCount }})
                </q-chip>
                <q-chip
                  v-if="rebootNeededCount > 0"
                  clickable
                  dense
                  size="sm"
                  :outline="!search.includes('is:rebootneeded')"
                  color="deep-orange"
                  text-color="white"
                  icon="restart_alt"
                  @click="setQuickFilter('is:rebootneeded')"
                >
                  {{ t("dash.quickReboot") }} ({{ rebootNeededCount }})
                </q-chip>
              </div>

              <q-space />

              <!-- Responsive Search & Action Controls -->
              <q-input
                v-model="search"
                style="min-width: 170px; max-width: 340px; flex: 1 1 200px"
                :label="t('dash.search')"
                dense
                outlined
                clearable
                @clear="clearFilter"
                class="q-pr-xs"
              >
                <template v-slot:prepend>
                  <q-icon name="search" color="primary" />
                </template>
                <template v-slot:after>
                  <q-btn
                    round
                    dense
                    flat
                    icon="filter_alt"
                    :color="isFilteringTable ? 'green' : ''"
                  >
                    <q-menu>
                      <q-list dense>
                        <q-item-label header>{{ t("dash.filterTable") }}</q-item-label>

                        <q-item>
                          <q-item-section side>
                            <q-checkbox v-model="filterChecksFailing" />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.checksFailing") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-checkbox v-model="filterPatchesPending" />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.patchesPending") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-checkbox v-model="filterActionsPending" />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.actionsPending") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-checkbox v-model="filterRebootNeeded" />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.rebootNeeded") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item-label header>{{ t("kpi.availability") }}</q-item-label>

                        <q-item>
                          <q-item-section side>
                            <q-radio val="all" v-model="filterAvailability" />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.showAllAgents") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-radio
                              val="online"
                              v-model="filterAvailability"
                            />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.showOnlineOnly") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-radio
                              val="offline"
                              v-model="filterAvailability"
                            />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.showOfflineOnly") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-radio
                              val="overdue"
                              v-model="filterAvailability"
                            />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.showOverdueOnly") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item>
                          <q-item-section side>
                            <q-radio
                              val="offline_30days"
                              v-model="filterAvailability"
                            />
                          </q-item-section>

                          <q-item-section>
                            <q-item-label>{{ t("dash.showOffline30Days") }}</q-item-label>
                          </q-item-section>
                        </q-item>
                      </q-list>

                      <div class="row no-wrap q-pa-md">
                        <div class="column">
                          <q-btn
                            v-close-popup
                            :label="t('dash.apply')"
                            color="primary"
                            @click="applyFilter"
                          />
                        </div>
                        <q-space />
                        <div class="column">
                          <q-btn :label="t('dash.clear')" @click="clearFilter" />
                        </div>
                      </div>
                    </q-menu>
                  </q-btn>
                  <q-btn
                    round
                    dense
                    flat
                    icon="analytics"
                    :color="showKpiBar ? 'primary' : ''"
                    @click="toggleKpiBar"
                  >
                    <q-tooltip>{{ t("dash.toggleKpis") }}</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    dense
                    flat
                    :icon="innerModel > 90 ? 'unfold_less' : 'unfold_more'"
                    color="primary"
                    @click="toggleBottomPanel"
                  >
                    <q-tooltip>{{ t("dash.maximizeTable") }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <AgentTable
              :agents="filteredAgents"
              :columns="localizedColumns"
              :search="search"
              :visibleColumns="visibleColumns"
            />
          </template>
          <template v-slot:separator>
            <q-avatar
              color="primary"
              text-color="white"
              size="20px"
              icon="drag_indicator"
            />
          </template>
          <template v-slot:after>
            <SubTableTabs />
          </template>
        </q-splitter>
      </template>
    </q-splitter>

    <!-- install agent modal -->
    <q-dialog v-model="showInstallAgentModal" @hide="closeInstallAgent">
      <InstallAgent @close="closeInstallAgent" :sitepk="parseInt(sitePk)" />
    </q-dialog>
  </q-page>
</template>

<script>
import mixins from "@/mixins/mixins";
import { openURL } from "quasar";
import { mapState } from "vuex";
import FileBar from "@/components/FileBar.vue";
import ExecutiveKPIBar from "@/components/dashboard/ExecutiveKPIBar.vue";
import AgentTable from "@/components/AgentTable.vue";
import SubTableTabs from "@/components/SubTableTabs.vue";
import PolicyAdd from "@/components/automation/modals/PolicyAdd.vue";
import ClientsForm from "@/components/clients/ClientsForm.vue";
import SitesForm from "@/components/clients/SitesForm.vue";
import DeleteClient from "@/components/clients/DeleteClient.vue";
import InstallAgent from "@/components/modals/agents/InstallAgent.vue";
import AlertTemplateAdd from "@/components/modals/alerts/AlertTemplateAdd.vue";
import IntegrationsContextMenu from "@/components/ui/IntegrationsContextMenu.vue";

import { removeClient, removeSite } from "@/api/clients";
import { t } from "@/i18n";

export default {
  name: "DashboardView",
  components: {
    FileBar,
    ExecutiveKPIBar,
    AgentTable,
    SubTableTabs,
    InstallAgent,
    IntegrationsContextMenu,
  },
  // allow child components to refresh table
  provide() {
    return {
      refreshDashboard: (clearTreeSelected, clearSubTable) => {
        if (clearSubTable) this.$store.commit("destroySubTable");

        this.$store.dispatch("refreshDashboard", clearTreeSelected);
      },
    };
  },
  mixins: [mixins],
  data() {
    return {
      showInstallAgentModal: false,
      sitePk: null,
      savedSidebarWidth: 15,
      innerModel: 48,
      search: this.$route.query.search ? this.$route.query.search : "",
      filterTextLength: 0,
      filterAvailability: "all",
      filterPatchesPending: false,
      filterActionsPending: false,
      filterChecksFailing: false,
      filterRebootNeeded: false,
      urlActions: [],
      columns: [
        {
          name: "smsalert",
          align: "left",
        },
        {
          name: "emailalert",
          align: "left",
        },
        {
          name: "dashboardalert",
          align: "left",
        },
        {
          name: "plat",
          label: "",
          field: "plat",
          sortable: true,
          align: "left",
        },
        {
          name: "mon-type",
          label: "",
          field: "monitoring_type",
          sortable: true,
          align: "left",
        },
        {
          name: "checks-status",
          align: "left",
          field: "checks",
          sortable: true,
          sort: (a, b) =>
            parseInt(b.failing) - parseInt(a.failing) ||
            parseInt(b.warning) - parseInt(a.warning) ||
            parseInt(b.info) - parseInt(a.info),
        },
        {
          name: "client_name",
          label: "Client",
          field: "client_name",
          sortable: true,
          align: "left",
        },
        {
          name: "site_name",
          label: "Site",
          field: "site_name",
          sortable: true,
          align: "left",
        },
        {
          name: "hostname",
          label: "Hostname",
          field: "hostname",
          sortable: true,
          align: "left",
        },
        {
          name: "quick_actions",
          label: "Quick Actions",
          field: "agent_id",
          sortable: false,
          align: "left",
        },
        {
          name: "description",
          label: "Description",
          field: "description",
          sortable: true,
          align: "left",
        },
        {
          name: "user",
          label: "User",
          field: "logged_username",
          sortable: true,
          align: "left",
        },
        {
          name: "italic",
          field: "italic",
        },
        {
          name: "patchespending",
          field: "has_patches_pending",
          align: "left",
          sortable: true,
        },
        {
          name: "pendingactions",
          field: "pending_actions_count",
          align: "left",
          sortable: true,
        },
        {
          name: "needs_reboot",
          field: "needs_reboot",
          align: "left",
          sortable: true,
        },
        {
          name: "agentstatus",
          field: "status",
          align: "left",
          sort: (a, b) => {
            const statusRank = {
              online: 0,
              offline: 1,
              overdue: 2,
            };
            return (statusRank[a] ?? 3) - (statusRank[b] ?? 3);
          },
          sortable: true,
        },
        {
          name: "last_seen",
          label: "Last Response",
          field: "last_seen",
          sortable: true,
          align: "left",
        },
        {
          name: "boot_time",
          label: "Boot Time",
          field: "boot_time",
          sortable: true,
          align: "left",
        },
      ],
      visibleColumns: [
        "smsalert",
        "plat",
        "mon-type",
        "emailalert",
        "dashboardalert",
        "checks-status",
        "client_name",
        "site_name",
        "hostname",
        "quick_actions",
        "description",
        "user",
        "patchespending",
        "pendingactions",
        "agentstatus",
        "needs_reboot",
        "last_seen",
        "boot_time",
      ],
    };
  },
  watch: {
    search(newVal) {
      if (newVal === "") this.clearFilter();
      else if (newVal.length < this.filterTextLength) this.clearFilter();
    },
    selectedTree() {
      if (this.clearSearchWhenSwitching) this.clearFilter();
    },
    tab() {
      this.$store.dispatch("loadAgents");
    },
    selectedRow(newVal) {
      if (newVal) {
        if (this.innerModel < 180) {
          this.innerModel = Math.round(Math.max(270, (this.$q.screen.height - 110) * 0.42));
          this.$store.commit("SET_SPLITTER", this.innerModel);
        }
      } else {
        this.innerModel = 48;
        this.$store.commit("SET_SPLITTER", this.innerModel);
      }
    },
  },
  methods: {
    t,
    toggleClientSidebar() {
      if (this.clientTreeSplitter > 2) {
        this.savedSidebarWidth = this.clientTreeSplitter;
        this.clientTreeSplitter = 0;
      } else {
        this.clientTreeSplitter = this.savedSidebarWidth || 15;
      }
    },
    toggleKpiBar() {
      this.$store.commit("SET_SHOW_KPI_BAR", !this.showKpiBar);
      this.$store.commit("SET_SPLITTER", this.innerModel);
    },
    toggleBottomPanel() {
      if (this.innerModel > 90) {
        this.innerModel = 48;
      } else {
        this.innerModel = Math.round(Math.max(270, (this.$q.screen.height - 110) * 0.44));
      }
      this.$store.commit("SET_SPLITTER", this.innerModel);
    },
    setQuickFilter(token) {
      if (this.search.trim() === token) {
        this.clearFilter();
      } else {
        this.search = token + " ";
        this.filterTextLength = token.length;
      }
    },
    getTree() {
      this.$store.dispatch("loadTree");
    },
    clearTreeSelected() {
      if (this.clearSearchWhenSwitching) this.clearFilter();
      this.$store.dispatch("refreshDashboard", true);
    },
    showPolicyAdd(node) {
      this.$q
        .dialog({
          component: PolicyAdd,
          componentProps: {
            type: node.children ? "client" : "site",
            object: node.children ? node.client : node.site,
          },
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showAddSiteModal(node) {
      this.$q
        .dialog({
          component: SitesForm,
          componentProps: {
            client: node.id,
          },
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showEditModal(node) {
      let props = {};
      if (node.children) {
        props.client = { id: node.id, name: node.label };
      } else {
        props.site = { id: node.id, name: node.label, client: node.client };
      }

      this.$q
        .dialog({
          component: node.children ? ClientsForm : SitesForm,
          componentProps: node.children
            ? { client: node.client }
            : { site: node.site },
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showDeleteModal(node) {
      if (
        (node.children && node.client.agent_count > 0) ||
        (!node.children && node.site.agent_count > 0)
      ) {
        this.$q
          .dialog({
            component: DeleteClient,
            componentProps: {
              object: node.children ? node.client : node.site,
              type: node.children ? "client" : "site",
            },
          })
          .onOk(this.clearTreeSelected);
      } else {
        this.$q
          .dialog({
            title: "Are you sure?",
            message: `Delete ${node.children ? "client" : "site"}: ${node.label}.`,
            cancel: true,
            ok: { label: "Delete", color: "negative" },
          })
          .onOk(async () => {
            this.$q.loading.show();
            try {
              const result = node.children
                ? await removeClient(node.id)
                : await removeSite(node.id);
              this.notifySuccess(result);
              this.clearTreeSelected();
            } catch (e) {
              console.error(e);
            }
            this.$q.loading.hide();
          });
      }
    },
    showInstallAgent(node) {
      this.sitePk = node.id;
      this.showInstallAgentModal = true;
    },
    closeInstallAgent() {
      this.showInstallAgentModal = false;
      this.sitePk = null;
    },
    showAlertTemplateAdd(node) {
      this.$q
        .dialog({
          component: AlertTemplateAdd,
          componentProps: {
            type: node.children ? "client" : "site",
            object: node.children ? node.client : node.site,
          },
        })
        .onOk(() => this.$store.dispatch("refreshDashboard"));
    },
    runChecks(node) {
      const target = node.children ? "client" : "site";
      this.$axios
        .post(`/checks/${target}/${node.id}/csbulkrun/`)
        .then((r) => {
          this.notifySuccess(r.data);
        })
        .catch((e) => {
          console.error(e);
        });
    },
    showToggleMaintenance(node) {
      let data = {
        id: node.id,
        type: node.raw.split("|")[0],
        action: node.color === "green" ? false : true,
      };

      this.$axios
        .post("/agents/maintenance/bulk/", data)
        .then((r) => {
          this.notifySuccess(r.data);
          this.$store.dispatch("refreshDashboard");
          this.$store.commit("setRefreshSummaryTab", true);
        })
        .catch((e) => {
          console.error(e);
        });
    },
    clearFilter() {
      this.filterTextLength = 0;
      this.filterPatchesPending = false;
      this.filterRebootNeeded = false;
      this.filterChecksFailing = false;
      this.filterActionsPending = false;
      this.filterAvailability = "all";
      this.search = "";
    },
    applyFilter() {
      // clear search if availability changes to all
      if (
        this.filterAvailability === "all" &&
        (this.search.includes("is:online") ||
          this.search.includes("is:offline") ||
          this.search.includes("is:expired") ||
          this.search.includes("is:overdue"))
      )
        this.clearFilter();

      // don't apply filter if nothing is being filtered
      if (!this.isFilteringTable) return;

      let filterText = "";

      if (this.filterPatchesPending) {
        filterText += "is:patchespending ";
      }

      if (this.filterActionsPending) {
        filterText += "is:actionspending ";
      }

      if (this.filterChecksFailing) {
        filterText += "is:checksfailing ";
      }

      if (this.filterRebootNeeded) {
        filterText += "is:rebootneeded ";
      }

      if (this.filterAvailability !== "all") {
        if (this.filterAvailability === "online") {
          filterText += "is:online ";
        } else if (this.filterAvailability === "offline") {
          filterText += "is:offline ";
        } else if (this.filterAvailability === "offline_30days") {
          filterText += "is:expired ";
        } else if (this.filterAvailability === "overdue") {
          filterText += "is:overdue ";
        }
      }

      this.search = filterText;
      this.filterTextLength = filterText.length - 1;
    },
    getURLActions() {
      this.$axios.get("/core/urlaction/").then((r) => {
        this.urlActions = r.data
          .filter((action) => action.action_type === "web")
          .sort((a, b) => a.name.localeCompare(b.name));
        if (this.urlActions.length === 0) {
          this.notifyWarning(
            "No URL Actions configured. Go to Settings > Global Settings > URL Actions",
          );
        }
      });
    },
    runURLAction(id, action, model) {
      const data = {
        [model]: id,
        action: action,
      };
      this.$axios.patch("/core/urlaction/run/", data).then((r) => {
        openURL(r.data);
      });
    },
  },
  computed: {
    ...mapState({
      clientsTree: (state) => state.tree,
      treeReady: (state) => state.treeReady,
      clearSearchWhenSwitching: (state) => state.clearSearchWhenSwitching,
      agents: (state) => state.agents,
      selectedRow: (state) => state.selectedRow,
      showKpiBar: (state) => state.showKpiBar,
    }),
    clientTreeSplitter: {
      get() {
        return this.$store.state.clientTreeSplitter;
      },
      set(newVal) {
        this.$store.dispatch("setClientTreeSplitter", newVal);
      },
    },
    tab: {
      get() {
        return this.$store.state.defaultAgentTblTab;
      },
      set(newVal) {
        this.$store.commit("SET_DEFAULT_AGENT_TBL_TAB", newVal);
        this.$store.commit("destroySubTable");
      },
    },
    selectedTree: {
      get() {
        return this.$store.state.selectedTree;
      },
      set(newVal) {
        this.$store.commit("setSelectedTree", newVal);
        this.$store.commit("destroySubTable");
      },
    },
    allClientsActive() {
      return this.selectedTree === "";
    },
    filteredAgents() {
      if (this.tab === "mixed") return this.agents;
      else return this.agents.filter((k) => k.monitoring_type === this.tab);
    },
    onlineCount() {
      return this.filteredAgents.filter((a) => a.status === "online").length;
    },
    offlineOrOverdueCount() {
      return this.filteredAgents.filter((a) => a.status !== "online").length;
    },
    failingChecksCount() {
      return this.filteredAgents.filter((a) => a.checks && a.checks.has_failing_checks).length;
    },
    patchesPendingCount() {
      return this.filteredAgents.filter((a) => a.has_patches_pending).length;
    },
    rebootNeededCount() {
      return this.filteredAgents.filter((a) => a.needs_reboot).length;
    },
    isFilteringTable() {
      return (
        this.filterPatchesPending ||
        this.filterActionsPending ||
        this.filterChecksFailing ||
        this.filterRebootNeeded ||
        this.filterAvailability !== "all"
      );
    },
    localizedColumns() {
      const labelMap = {
        client_name: this.t("dash.colClient"),
        site_name: this.t("dash.colSite"),
        hostname: this.t("dash.colHostname"),
        quick_actions: this.t("dash.colQuickActions"),
        description: this.t("dash.colDescription"),
        user: this.t("dash.colUser"),
        last_seen: this.t("dash.colLastSeen"),
        boot_time: this.t("dash.colBootTime"),
      };
      return this.columns.map((col) =>
        labelMap[col.name] ? { ...col, label: labelMap[col.name] } : col,
      );
    },
  },
  mounted() {
    this.getTree();
    if (this.$q.screen.width < 1100 && this.clientTreeSplitter > 12) {
      this.clientTreeSplitter = 0;
    }

    // set initial value for agent table and agent tabs
    this.$store.commit("SET_SPLITTER", this.innerModel);
  },
};
</script>

<style>
.my-menu-link {
  color: white;
  background: lightgray;
}
</style>
