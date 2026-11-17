<template>
  <q-page class="column no-wrap overflow-hidden" style="height: calc(100vh - 50px)">
    <FileBar style="flex: 0 0 auto" />
    <ExecutiveKPIBar v-if="showKpiBar" style="flex: 0 0 auto" />
    <q-splitter
      v-model="clientTreeSplitter"
      :limits="[0, 40]"
      class="col full-width"
      style="min-height: 0"
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
          class="q-pa-sm q-gutter-sm trmm-scroll-pane"
          style="height: 100%; overflow-y: auto; overscroll-behavior: contain"
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
          class="fit"
          @update:model-value="$store.commit('SET_SPLITTER', innerModel)"
          after-class="column no-wrap overflow-hidden"
          before-class="column no-wrap overflow-hidden"
          emit-immediately
        >
          <template v-slot:before>
            <div class="row items-center wrap q-px-xs q-py-xs q-gutter-xs" style="flex: 0 0 auto">
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
                <q-tab
                  name="server"
                  icon="fas fa-server"
                  :label="`${t('nav.servers')} (${serverTabCount})`"
                />
                <q-tab
                  name="workstation"
                  icon="computer"
                  :label="`${t('nav.workstations')} (${workstationTabCount})`"
                />
                <q-tab
                  name="mixed"
                  :label="`${t('dash.mixed')} (${agents.length})`"
                />
              </q-tabs>

              <!-- 1-Click Quick Category Chips -->
              <div class="row items-center wrap q-gutter-xs" data-no-translate="true">
                <q-chip
                  clickable
                  dense
                  size="12px"
                  :color="!hasAnyTokenFilter ? 'primary' : 'grey-8'"
                  text-color="white"
                  @click="clearFilter"
                >
                  {{ t("dash.quickAll") }} ({{ filteredAgents.length }})
                </q-chip>
                <q-chip
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:online') ? 'positive' : 'grey-8'"
                  text-color="white"
                  icon="check_circle"
                  @click="setQuickFilter('is:online')"
                >
                  {{ t("dash.quickOnline") }} ({{ onlineCount }})
                  <q-tooltip>Máquinas conectadas e respondendo em tempo real</q-tooltip>
                </q-chip>
                <q-chip
                  v-if="offlineOnlyCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:offline') ? 'warning' : 'grey-8'"
                  :text-color="hasToken('is:offline') ? 'black' : 'white'"
                  icon="power_off"
                  @click="setQuickFilter('is:offline')"
                >
                  {{ t("dash.quickOffline") }} ({{ offlineOnlyCount }})
                </q-chip>
                <q-chip
                  v-if="overdueOnlyCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:overdue') ? 'deep-orange' : 'grey-8'"
                  text-color="white"
                  icon="schedule"
                  @click="setQuickFilter('is:overdue')"
                >
                  {{ t("dash.overdue") }} ({{ overdueOnlyCount }})
                  <q-tooltip>Máquinas que passaram do tempo de check-in (Overdue)</q-tooltip>
                </q-chip>
                <q-chip
                  v-if="offlineOrOverdueCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:disconnected') ? 'brown-7' : 'grey-8'"
                  text-color="white"
                  icon="cloud_off"
                  @click="setQuickFilter('is:disconnected')"
                >
                  Desconectados ({{ offlineOrOverdueCount }})
                  <q-tooltip>Mostra todos Offline ({{ offlineOnlyCount }}) + Vencidos ({{ overdueOnlyCount }}) juntos</q-tooltip>
                </q-chip>
                <q-chip
                  v-if="failingChecksCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:checksfailing') ? 'negative' : 'grey-8'"
                  text-color="white"
                  icon="warning"
                  @click="setQuickFilter('is:checksfailing')"
                >
                  {{ t("dash.quickFailing") }} ({{ failingChecksCount }})
                </q-chip>
                <q-chip
                  v-if="rebootNeededCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:rebootneeded') ? 'orange-9' : 'grey-8'"
                  text-color="white"
                  icon="restart_alt"
                  @click="setQuickFilter('is:rebootneeded')"
                >
                  {{ t("dash.quickReboot") }} ({{ rebootNeededCount }})
                </q-chip>
                <q-chip
                  v-if="outsideAdCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:outsidead') ? 'amber-9' : 'grey-8'"
                  text-color="white"
                  icon="domain_disabled"
                  @click="setQuickFilter('is:outsidead')"
                >
                  Fora do AD ({{ outsideAdCount }})
                </q-chip>
                <q-chip
                  v-if="linuxCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:linux') ? 'light-blue-8' : 'grey-8'"
                  text-color="white"
                  icon="mdi-linux"
                  @click="setQuickFilter('is:linux')"
                >
                  Linux ({{ linuxCount }})
                </q-chip>
                <q-chip
                  v-if="darwinCount > 0"
                  clickable
                  dense
                  size="12px"
                  :color="hasToken('is:darwin') ? 'blue-grey-6' : 'grey-8'"
                  text-color="white"
                  icon="mdi-apple"
                  @click="setQuickFilter('is:darwin')"
                >
                  macOS ({{ darwinCount }})
                </q-chip>
                <q-chip
                  clickable
                  dense
                  size="12px"
                  color="teal-7"
                  text-color="white"
                  icon="sync"
                  @click="runFullFleetSync"
                >
                  Sincronizar 100%
                  <q-tooltip>
                    Verifica todos os agentes offline/vencidos via NATS em tempo real, remove duplicatas de máquinas formatadas e atualiza todos os contadores
                  </q-tooltip>
                </q-chip>
                <q-chip
                  clickable
                  dense
                  size="12px"
                  color="indigo-7"
                  text-color="white"
                  icon="account_tree"
                  @click="showADDirectoryAuditModal = true"
                >
                  Auditoria AD
                  <q-tooltip>
                    Consulta o Active Directory (pastas CRD, Computadores, Computers, sub-OUs e raiz do domínio) e mostra computadores faltantes no Tactical RMM com Push Remoto em 1 clique
                  </q-tooltip>
                </q-chip>
              </div>

              <q-space />

              <!-- Search & Synced Advanced Filter Control -->
              <q-input
                v-model="search"
                style="min-width: 240px; width: 290px"
                label="Pesquisar PC, usuário, IP..."
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
                    :color="isFilteringTable ? 'positive' : ''"
                  >
                    <q-badge v-if="activeFilterCount > 0" color="positive" floating>
                      {{ activeFilterCount }}
                    </q-badge>
                    <q-tooltip>Filtros Avançados ({{ activeFilterCount }} ativos)</q-tooltip>
                    <q-menu style="min-width: 295px; max-height: 70vh; overflow-y: auto">
                      <q-list dense class="trmm-scroll-pane">
                        <q-item-label header class="text-weight-bold text-primary">
                          Saúde &amp; Manutenção
                        </q-item-label>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-checkbox v-model="filterChecksFailing" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.checksFailing") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-checkbox v-model="filterPatchesPending" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.patchesPending") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-checkbox v-model="filterActionsPending" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.actionsPending") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-checkbox v-model="filterRebootNeeded" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.rebootNeeded") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-checkbox v-model="filterMaintenance" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Em Modo de Manutenção</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-separator class="q-my-xs" />

                        <q-item-label header class="text-weight-bold text-primary">
                          {{ t("kpi.availability") }}
                        </q-item-label>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="all" v-model="filterAvailability" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.showAllAgents") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="online" v-model="filterAvailability" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.showOnlineOnly") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="disconnected" v-model="filterAvailability" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Desconectados (Offline + Vencidos)</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="offline" v-model="filterAvailability" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.showOfflineOnly") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="overdue" v-model="filterAvailability" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Apenas Vencidos / Overdue</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="offline_30days" v-model="filterAvailability" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>{{ t("dash.showOffline30Days") }}</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-separator class="q-my-xs" />

                        <q-item-label header class="text-weight-bold text-primary">
                          Sistema Operacional
                        </q-item-label>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="all" v-model="filterPlatform" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Todos os Sistemas</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="windows" v-model="filterPlatform" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Windows</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="linux" v-model="filterPlatform" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Linux</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="darwin" v-model="filterPlatform" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>macOS</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-separator class="q-my-xs" />

                        <q-item-label header class="text-weight-bold text-primary">
                          Active Directory (AD)
                        </q-item-label>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="all" v-model="filterAdStatus" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Todos</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="inad" v-model="filterAdStatus" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Ingressados no AD</q-item-label>
                          </q-item-section>
                        </q-item>

                        <q-item tag="label" clickable v-ripple>
                          <q-item-section side>
                            <q-radio val="outsidead" v-model="filterAdStatus" @update:model-value="applyFilter" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>Fora do AD / Workgroup</q-item-label>
                          </q-item-section>
                        </q-item>
                      </q-list>

                      <div class="row no-wrap q-pa-sm q-gutter-sm justify-between">
                        <q-btn
                          outline
                          no-caps
                          dense
                          color="grey"
                          :label="t('dash.clear')"
                          @click="clearFilter"
                        />
                        <q-btn
                          v-close-popup
                          unelevated
                          no-caps
                          dense
                          color="primary"
                          label="Fechar"
                        />
                      </div>
                    </q-menu>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col full-width overflow-hidden" style="min-height: 0">
              <AgentTable
                :agents="filteredAgents"
                :columns="localizedColumns"
                :search="search"
                :visibleColumns="visibleColumns"
              />
            </div>
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

    <!-- active directory full audit modal -->
    <q-dialog v-model="showADDirectoryAuditModal">
      <ADDirectoryAuditModal @close="showADDirectoryAuditModal = false" />
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
import ADDirectoryAuditModal from "@/components/modals/agents/ADDirectoryAuditModal.vue";
import AlertTemplateAdd from "@/components/modals/alerts/AlertTemplateAdd.vue";
import IntegrationsContextMenu from "@/components/ui/IntegrationsContextMenu.vue";

import { removeClient, removeSite } from "@/api/clients";
import { fetchFleetExecutiveSummary, fleetDomainMap, syncAndCleanupFleet } from "@/api/enhanced";
import { useDashboardStore } from "@/stores/dashboard";
import { t } from "@/i18n";

export default {
  name: "DashboardView",
  components: {
    FileBar,
    ExecutiveKPIBar,
    AgentTable,
    SubTableTabs,
    InstallAgent,
    ADDirectoryAuditModal,
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
      showADDirectoryAuditModal: false,
      sitePk: null,
      savedSidebarWidth: 15,
      innerModel: (this.$q.screen.height - 82) / 2,
      search: this.$route.query.search ? this.$route.query.search : "",
      filterTextLength: 0,
      filterAvailability: "all",
      filterPlatform: "all",
      filterAdStatus: "all",
      filterPatchesPending: false,
      filterActionsPending: false,
      filterChecksFailing: false,
      filterRebootNeeded: false,
      filterMaintenance: false,
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
      if (newVal === "" || newVal === null) {
        this.resetFilterStateOnly();
      } else {
        this.syncFiltersFromSearch(newVal);
      }
    },
    selectedTree() {
      if (this.clearSearchWhenSwitching) this.clearFilter();
    },
    tab() {
      this.$store.dispatch("loadAgents");
    },
  },
  methods: {
    t,
    hasToken(token) {
      const tokens = String(this.search || "")
        .toLowerCase()
        .trim()
        .split(/\s+/);
      return tokens.includes(token.toLowerCase());
    },
    resetFilterStateOnly() {
      this.filterTextLength = 0;
      this.filterPatchesPending = false;
      this.filterRebootNeeded = false;
      this.filterChecksFailing = false;
      this.filterActionsPending = false;
      this.filterMaintenance = false;
      this.filterAvailability = "all";
      this.filterPlatform = "all";
      this.filterAdStatus = "all";
    },
    syncFiltersFromSearch(val) {
      const tokens = String(val || "")
        .toLowerCase()
        .trim()
        .split(/\s+/)
        .filter(Boolean);

      this.filterChecksFailing = tokens.includes("is:checksfailing");
      this.filterPatchesPending = tokens.includes("is:patchespending");
      this.filterActionsPending = tokens.includes("is:actionspending");
      this.filterRebootNeeded = tokens.includes("is:rebootneeded");
      this.filterMaintenance = tokens.includes("is:maintenance");

      if (tokens.includes("is:online")) this.filterAvailability = "online";
      else if (tokens.includes("is:disconnected")) this.filterAvailability = "disconnected";
      else if (tokens.includes("is:offline")) this.filterAvailability = "offline";
      else if (tokens.includes("is:overdue")) this.filterAvailability = "overdue";
      else if (tokens.includes("is:expired")) this.filterAvailability = "offline_30days";
      else this.filterAvailability = "all";

      if (tokens.includes("is:windows")) this.filterPlatform = "windows";
      else if (tokens.includes("is:linux")) this.filterPlatform = "linux";
      else if (tokens.includes("is:darwin")) this.filterPlatform = "darwin";
      else this.filterPlatform = "all";

      if (tokens.includes("is:outsidead")) this.filterAdStatus = "outsidead";
      else if (tokens.includes("is:inad")) this.filterAdStatus = "inad";
      else this.filterAdStatus = "all";
    },
    async runFullFleetSync() {
      this.$q.loading.show({ message: "Sincronizando 100% dos agentes via NATS e limpando duplicatas..." });
      try {
        const res = await syncAndCleanupFleet({ deduplicate: true, wake_overdue: true, verify_online: true });
        await this.$store.dispatch("refreshDashboard");
        useDashboardStore().triggerSummaryRefresh();
        const demotedPart = res.demoted_count ? `, Falso-online corrigidos: ${res.demoted_count}` : "";
        this.notifySuccess(
          `Sincronização concluída! Online: ${res.online} | Offline: ${res.offline} | Vencidos: ${res.overdue} (Reativados: ${res.recovered_count}${demotedPart}, Duplicatas limpas: ${res.deduplicated_count})`,
        );
      } catch (e) {
        this.$store.dispatch("refreshDashboard");
      } finally {
        this.$q.loading.hide();
      }
    },
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
      const availTokens = ["is:online", "is:offline", "is:overdue", "is:disconnected", "is:expired"];
      const platTokens = ["is:windows", "is:linux", "is:darwin"];
      const adTokens = ["is:outsidead", "is:inad"];
      const rawTokens = String(this.search || "").trim().split(/\s+/).filter(Boolean);
      const lowToken = token.toLowerCase();
      const exists = rawTokens.some((tItem) => tItem.toLowerCase() === lowToken);

      let nextTokens;
      if (exists) {
        nextTokens = rawTokens.filter((tItem) => tItem.toLowerCase() !== lowToken);
      } else {
        nextTokens = rawTokens.filter((tItem) => {
          const low = tItem.toLowerCase();
          if (availTokens.includes(lowToken) && availTokens.includes(low)) return false;
          if (platTokens.includes(lowToken) && platTokens.includes(low)) return false;
          if (adTokens.includes(lowToken) && adTokens.includes(low)) return false;
          return true;
        });
        nextTokens.push(token);
      }

      const nextStr = nextTokens.join(" ");
      this.search = nextStr ? `${nextStr} ` : "";
      this.filterTextLength = this.search.length;
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
      this.resetFilterStateOnly();
      this.search = "";
    },
    applyFilter() {
      // Preserve any plain-text search words user typed while rebuilding is:* tokens
      const freeWords = String(this.search || "")
        .trim()
        .split(/\s+/)
        .filter((w) => w && !w.toLowerCase().startsWith("is:"));

      const tokens = [];

      if (this.filterChecksFailing) tokens.push("is:checksfailing");
      if (this.filterPatchesPending) tokens.push("is:patchespending");
      if (this.filterActionsPending) tokens.push("is:actionspending");
      if (this.filterRebootNeeded) tokens.push("is:rebootneeded");
      if (this.filterMaintenance) tokens.push("is:maintenance");

      if (this.filterAvailability === "online") tokens.push("is:online");
      else if (this.filterAvailability === "disconnected") tokens.push("is:disconnected");
      else if (this.filterAvailability === "offline") tokens.push("is:offline");
      else if (this.filterAvailability === "overdue") tokens.push("is:overdue");
      else if (this.filterAvailability === "offline_30days") tokens.push("is:expired");

      if (this.filterPlatform !== "all") tokens.push(`is:${this.filterPlatform}`);
      if (this.filterAdStatus !== "all") tokens.push(`is:${this.filterAdStatus}`);

      const combined = [...tokens, ...freeWords].join(" ").trim();
      this.search = combined ? `${combined} ` : "";
      this.filterTextLength = this.search.length;
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
    serverTabCount() {
      return this.agents.filter((a) => a.monitoring_type === "server").length;
    },
    workstationTabCount() {
      return this.agents.filter((a) => a.monitoring_type === "workstation").length;
    },
    filteredAgents() {
      if (this.tab === "mixed") return this.agents;
      else return this.agents.filter((k) => k.monitoring_type === this.tab);
    },
    windowsCount() {
      return this.filteredAgents.filter((a) => a.plat === "windows").length;
    },
    linuxCount() {
      return this.filteredAgents.filter((a) => a.plat === "linux").length;
    },
    darwinCount() {
      return this.filteredAgents.filter((a) => a.plat === "darwin").length;
    },
    onlineCount() {
      return this.filteredAgents.filter((a) => a.status === "online").length;
    },
    offlineOnlyCount() {
      return this.filteredAgents.filter((a) => a.status === "offline").length;
    },
    overdueOnlyCount() {
      return this.filteredAgents.filter((a) => a.status === "overdue").length;
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
    outsideAdCount() {
      const map = fleetDomainMap.value || {};
      return this.filteredAgents.filter(
        (a) => map[a.agent_id] && map[a.agent_id].part_of_domain === false,
      ).length;
    },
    insideAdCount() {
      const map = fleetDomainMap.value || {};
      return this.filteredAgents.filter(
        (a) => map[a.agent_id] && map[a.agent_id].part_of_domain === true,
      ).length;
    },
    hasAnyTokenFilter() {
      return String(this.search || "").trim().length > 0;
    },
    activeFilterCount() {
      let c = 0;
      if (this.filterPatchesPending) c += 1;
      if (this.filterActionsPending) c += 1;
      if (this.filterChecksFailing) c += 1;
      if (this.filterRebootNeeded) c += 1;
      if (this.filterMaintenance) c += 1;
      if (this.filterAvailability !== "all") c += 1;
      if (this.filterPlatform !== "all") c += 1;
      if (this.filterAdStatus !== "all") c += 1;
      return c;
    },
    isFilteringTable() {
      return this.activeFilterCount > 0;
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
    if (Object.keys(fleetDomainMap.value || {}).length === 0) {
      fetchFleetExecutiveSummary().catch(() => {});
    }
    if (this.$q.screen.width < 1100 && this.clientTreeSplitter > 12) {
      this.clientTreeSplitter = 0;
    }

    // set initial value for agent table and agent tabs
    this.$store.commit("SET_SPLITTER", this.innerModel);

    // Auto-refresh agent list & counters every 30s
    this._dashSyncTimer = setInterval(() => {
      this.$store.dispatch("getDashInfo", false);
      this.$store.dispatch("loadAgents");
      this.$store.dispatch("loadTree");
      useDashboardStore().triggerSummaryRefresh();
    }, 30000);
  },
  beforeUnmount() {
    if (this._dashSyncTimer) {
      clearInterval(this._dashSyncTimer);
    }
  },
};
</script>

<style>
.my-menu-link {
  color: white;
  background: lightgray;
}
</style>
