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
                <div class="row items-center no-wrap full-width">
                  <q-icon
                    :name="props.node.icon"
                    :color="props.node.color"
                    size="16px"
                    class="q-mr-xs"
                  />
                  <div class="ellipsis text-weight-medium">
                    {{ props.node.label }}
                    <q-tooltip :delay="600">
                      ID: {{ props.node.id }}<br />
                      Equipamentos:
                      {{
                        props.node.children
                          ? props.node.client.agent_count
                          : props.node.site.agent_count
                      }}
                    </q-tooltip>
                  </div>
                  <q-space />
                  <q-badge
                    rounded
                    :color="$q.dark.isActive ? 'blue-grey-9' : 'blue-grey-2'"
                    :text-color="$q.dark.isActive ? 'grey-3' : 'blue-grey-9'"
                    class="q-ml-xs text-weight-bold"
                    style="font-size: 10px; padding: 2px 6px"
                  >
                    {{
                      props.node.children
                        ? props.node.client.agent_count
                        : props.node.site.agent_count
                    }}
                  </q-badge>

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

              <!-- 1-Click Quick Filter Pills & Enterprise Actions -->
              <div class="row items-center wrap trmm-toolbar-group" data-no-translate="true">
                <!-- Filter Pills -->
                <q-btn
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-primary': !hasAnyTokenFilter }"
                  @click="clearFilter"
                >
                  <q-icon name="grid_view" size="15px" class="q-mr-xs" :color="!hasAnyTokenFilter ? 'white' : 'primary'" />
                  <span>{{ t("dash.quickAll") }}</span>
                  <span class="trmm-pill-count">{{ filteredAgents.length }}</span>
                </q-btn>

                <q-btn
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-positive': hasToken('is:online') }"
                  @click="setQuickFilter('is:online')"
                >
                  <span class="trmm-status-dot trmm-status-dot--online q-mr-xs" />
                  <span>{{ t("dash.quickOnline") }}</span>
                  <span class="trmm-pill-count">{{ onlineCount }}</span>
                  <q-tooltip>Máquinas conectadas e respondendo em tempo real</q-tooltip>
                </q-btn>

                <q-btn
                  v-if="offlineOnlyCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-warning': hasToken('is:offline') }"
                  @click="setQuickFilter('is:offline')"
                >
                  <q-icon name="cloud_off" size="15px" class="q-mr-xs" :color="hasToken('is:offline') ? 'black' : 'amber-5'" />
                  <span>{{ t("dash.quickOffline") }}</span>
                  <span class="trmm-pill-count">{{ offlineOnlyCount }}</span>
                </q-btn>

                <q-btn
                  v-if="overdueOnlyCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-negative': hasToken('is:overdue') }"
                  @click="setQuickFilter('is:overdue')"
                >
                  <q-icon name="schedule" size="15px" class="q-mr-xs" :color="hasToken('is:overdue') ? 'white' : 'deep-orange-4'" />
                  <span>{{ t("dash.overdue") }}</span>
                  <span class="trmm-pill-count">{{ overdueOnlyCount }}</span>
                  <q-tooltip>Máquinas que passaram do tempo de check-in (Overdue)</q-tooltip>
                </q-btn>

                <q-btn
                  v-if="offlineOrOverdueCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-negative': hasToken('is:disconnected') }"
                  @click="setQuickFilter('is:disconnected')"
                >
                  <q-icon name="wifi_off" size="15px" class="q-mr-xs" :color="hasToken('is:disconnected') ? 'white' : 'orange-4'" />
                  <span>Desconectados</span>
                  <span class="trmm-pill-count">{{ offlineOrOverdueCount }}</span>
                  <q-tooltip>Mostra todos Offline ({{ offlineOnlyCount }}) + Vencidos ({{ overdueOnlyCount }}) juntos</q-tooltip>
                </q-btn>

                <q-btn
                  v-if="failingChecksCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-negative': hasToken('is:checksfailing') }"
                  @click="setQuickFilter('is:checksfailing')"
                >
                  <q-icon name="error_outline" size="15px" class="q-mr-xs" :color="hasToken('is:checksfailing') ? 'white' : 'red-4'" />
                  <span>{{ t("dash.quickFailing") }}</span>
                  <span class="trmm-pill-count">{{ failingChecksCount }}</span>
                </q-btn>

                <q-btn
                  v-if="rebootNeededCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-warning': hasToken('is:rebootneeded') }"
                  @click="setQuickFilter('is:rebootneeded')"
                >
                  <q-icon name="restart_alt" size="15px" class="q-mr-xs" :color="hasToken('is:rebootneeded') ? 'black' : 'orange-4'" />
                  <span>{{ t("dash.quickReboot") }}</span>
                  <span class="trmm-pill-count">{{ rebootNeededCount }}</span>
                </q-btn>

                <q-btn
                  v-if="outsideAdCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-amber': hasToken('is:outsidead') }"
                  @click="setQuickFilter('is:outsidead')"
                >
                  <q-icon name="domain_disabled" size="15px" class="q-mr-xs" :color="hasToken('is:outsidead') ? 'white' : 'amber-5'" />
                  <span>Fora do AD</span>
                  <span class="trmm-pill-count">{{ outsideAdCount }}</span>
                </q-btn>

                <q-btn
                  v-if="linuxCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-primary': hasToken('is:linux') }"
                  @click="setQuickFilter('is:linux')"
                >
                  <q-icon name="terminal" size="15px" class="q-mr-xs" :color="hasToken('is:linux') ? 'white' : 'light-blue-4'" />
                  <span>Linux</span>
                  <span class="trmm-pill-count">{{ linuxCount }}</span>
                </q-btn>

                <q-btn
                  v-if="darwinCount > 0"
                  dense
                  no-caps
                  unelevated
                  class="trmm-filter-pill"
                  :class="{ 'trmm-filter-pill--active-primary': hasToken('is:darwin') }"
                  @click="setQuickFilter('is:darwin')"
                >
                  <q-icon name="laptop_mac" size="15px" class="q-mr-xs" :color="hasToken('is:darwin') ? 'white' : 'blue-grey-3'" />
                  <span>macOS</span>
                  <span class="trmm-pill-count">{{ darwinCount }}</span>
                </q-btn>

                <q-separator vertical inset class="q-mx-xs" style="height: 20px; align-self: center" />

                <!-- Enterprise Action Buttons -->
                <q-btn
                  dense
                  no-caps
                  unelevated
                  class="trmm-action-btn trmm-action-btn--sync"
                  @click="runFullFleetSync"
                >
                  <q-icon name="autorenew" size="16px" class="q-mr-xs" />
                  <span>Sincronizar</span>
                  <q-tooltip>
                    Verifica todos os agentes offline/vencidos via NATS em tempo real, remove duplicatas e atualiza todos os contadores
                  </q-tooltip>
                </q-btn>

                <q-btn
                  dense
                  no-caps
                  unelevated
                  class="trmm-action-btn trmm-action-btn--ad"
                  @click="showADDirectoryAuditModal = true"
                >
                  <q-icon name="hub" size="16px" class="q-mr-xs" />
                  <span>Auditoria AD</span>
                  <q-tooltip>
                    Consulta o Active Directory e mostra computadores faltantes no Tactical RMM com Push Remoto em 1 clique
                  </q-tooltip>
                </q-btn>

                <q-btn
                  dense
                  no-caps
                  unelevated
                  class="trmm-action-btn trmm-action-btn--inventory"
                  @click="showInventoryManagerModal = true"
                >
                  <q-icon name="inventory_2" size="16px" class="q-mr-xs" />
                  <span>Inventário &amp; Patrimônio</span>
                  <q-tooltip>
                    Gerencia Nº de Patrimônio, Ativos e Passivos de Rede, Equipamentos Clínicos, importação CSV e exportação Excel/PDF por unidade
                  </q-tooltip>
                </q-btn>

                <q-btn
                  dense
                  no-caps
                  unelevated
                  class="trmm-action-btn trmm-action-btn--reports"
                  @click="showFleetReportsModal = true"
                >
                  <q-icon name="assessment" size="16px" class="q-mr-xs" />
                  <span>Relatórios</span>
                  <q-tooltip>
                    Abre a Central de Relatórios Corporativos (AD, Patches, Offline e Exportação Excel/PDF)
                  </q-tooltip>
                </q-btn>
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

    <!-- consolidated inventory, patrimonio & network active/passive modal -->
    <q-dialog
      v-model="showInventoryManagerModal"
      maximized
      transition-show="slide-up"
      transition-hide="slide-down"
    >
      <InventoryManagerModal
        :initialSiteId="sitePk ? parseInt(sitePk) : null"
        @close="showInventoryManagerModal = false"
      />
    </q-dialog>

    <!-- Fleet Reports Modal -->
    <q-dialog
      v-model="showFleetReportsModal"
      maximized
      transition-show="slide-up"
      transition-hide="slide-down"
    >
      <FleetReportsModal
        initialReportType="all"
        @close="showFleetReportsModal = false"
      />
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
import InventoryManagerModal from "@/components/modals/agents/InventoryManagerModal.vue";
import FleetReportsModal from "@/components/modals/reports/FleetReportsModal.vue";
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
    InventoryManagerModal,
    FleetReportsModal,
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
      showInventoryManagerModal: false,
      showFleetReportsModal: false,
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

.trmm-toolbar-group {
  gap: 6px;
}

.trmm-filter-pill {
  border-radius: 7px !important;
  padding: 2px 9px !important;
  min-height: 28px !important;
  font-size: 12px !important;
  font-weight: 500;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(148, 163, 184, 0.1);
  transition: all 0.15s ease;
}

.trmm-filter-pill:hover {
  border-color: rgba(148, 163, 184, 0.5);
  background: rgba(148, 163, 184, 0.18);
}

.trmm-filter-pill--active-primary {
  background: var(--q-primary, #1976d2) !important;
  border-color: var(--q-primary, #1976d2) !important;
  color: #ffffff !important;
  box-shadow: 0 1px 6px rgba(25, 118, 210, 0.35);
}

.trmm-filter-pill--active-positive {
  background: #16a34a !important;
  border-color: #16a34a !important;
  color: #ffffff !important;
  box-shadow: 0 1px 6px rgba(22, 163, 74, 0.35);
}

.trmm-filter-pill--active-warning {
  background: #f59e0b !important;
  border-color: #f59e0b !important;
  color: #111827 !important;
}

.trmm-filter-pill--active-amber {
  background: #d97706 !important;
  border-color: #d97706 !important;
  color: #ffffff !important;
}

.trmm-filter-pill--active-negative {
  background: #dc2626 !important;
  border-color: #dc2626 !important;
  color: #ffffff !important;
}

.trmm-pill-count {
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 17px;
  background: rgba(0, 0, 0, 0.24);
}

body.body--light .trmm-filter-pill:not([class*="trmm-filter-pill--active"]) .trmm-pill-count {
  background: rgba(15, 23, 42, 0.1);
  color: #0f172a;
}

.trmm-status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.trmm-status-dot--online {
  background: #22c55e;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.28);
}

.trmm-filter-pill--active-positive .trmm-status-dot--online {
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.35);
}

.trmm-action-btn {
  border-radius: 7px !important;
  padding: 2px 11px !important;
  min-height: 28px !important;
  font-size: 12px !important;
  font-weight: 600;
  transition: all 0.15s ease;
}

.trmm-action-btn--sync {
  background: rgba(13, 148, 136, 0.18) !important;
  border: 1px solid rgba(45, 212, 191, 0.42);
  color: #2dd4bf !important;
}
.trmm-action-btn--sync:hover {
  background: rgba(13, 148, 136, 0.32) !important;
}
body.body--light .trmm-action-btn--sync {
  color: #0f766e !important;
  border-color: rgba(15, 118, 110, 0.4);
}

.trmm-action-btn--ad {
  background: rgba(99, 102, 241, 0.18) !important;
  border: 1px solid rgba(129, 140, 248, 0.42);
  color: #a5b4fc !important;
}
.trmm-action-btn--ad:hover {
  background: rgba(99, 102, 241, 0.32) !important;
}
body.body--light .trmm-action-btn--ad {
  color: #4338ca !important;
  border-color: rgba(67, 56, 202, 0.4);
}

.trmm-action-btn--inventory {
  background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
  border: 1px solid rgba(45, 212, 191, 0.45);
  color: #ffffff !important;
  box-shadow: 0 1px 6px rgba(13, 148, 136, 0.35);
}
.trmm-action-btn--inventory:hover {
  filter: brightness(1.1);
}

.trmm-action-btn--reports {
  background: rgba(2, 132, 199, 0.18) !important;
  border: 1px solid rgba(56, 189, 248, 0.42);
  color: #38bdf8 !important;
}
.trmm-action-btn--reports:hover {
  background: rgba(2, 132, 199, 0.32) !important;
}
body.body--light .trmm-action-btn--reports {
  color: #0369a1 !important;
  border-color: rgba(3, 105, 161, 0.4);
}
</style>
