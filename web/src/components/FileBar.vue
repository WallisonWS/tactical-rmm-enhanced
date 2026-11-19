<template>
  <div class="q-pb-sm">
    <q-bar>
      <q-btn-group flat>
        <q-btn size="md" dense no-caps flat :label="t('filebar.file')">
          <q-menu>
            <q-list dense style="min-width: 100px">
              <q-item clickable>
                <q-item-section>{{ t("filebar.add") }}</q-item-section>
                <q-item-section side>
                  <q-icon name="keyboard_arrow_right" />
                </q-item-section>
                <q-menu anchor="top right" self="top left">
                  <q-list dense style="min-width: 100px">
                    <q-item clickable v-close-popup @click="showAddClientModal">
                      <q-item-section>{{ t("filebar.client") }}</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="showAddSiteModal">
                      <q-item-section>{{ t("filebar.site") }}</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-item>

              <q-item clickable v-close-popup @click="showAuditManager">
                <q-item-section>{{ t("filebar.auditLog") }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showDebugLog">
                <q-item-section>{{ t("filebar.debugLog") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- view -->
        <q-btn size="md" dense no-caps flat :label="t('filebar.view')">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showPendingActions">
                <q-item-section>{{ t("filebar.pendingActions") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- agents -->
        <q-btn size="md" dense no-caps flat :label="t('filebar.agents')">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="showInstallAgent = true">
                <q-item-section>{{ t("filebar.installAgent") }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showADDirectoryAuditModal = true">
                <q-item-section>Auditoria AD × Tactical (Computadores Faltantes)</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showInventoryManagerModal = true">
                <q-item-section>Inventário, Patrimônio &amp; Ativos/Passivos de Rede</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="showDeployments">
                <q-item-section>{{ t("filebar.manageDeployments") }}</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="showUpdateAgentsModal = true"
              >
                <q-item-section>{{ t("filebar.updateAgents") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>

        <!-- settings -->
        <q-btn size="md" dense no-caps flat :label="t('filebar.settings')">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <!-- clients manager -->
              <q-item clickable v-close-popup @click="showClientsManager">
                <q-item-section>{{ t("filebar.clientsManager") }}</q-item-section>
              </q-item>
              <!-- script manager -->
              <q-item clickable v-close-popup @click="showScriptManager">
                <q-item-section>{{ t("filebar.scriptManager") }}</q-item-section>
              </q-item>
              <!-- automation manager -->
              <q-item clickable v-close-popup @click="showAutomationManager">
                <q-item-section>{{ t("filebar.automationManager") }}</q-item-section>
              </q-item>
              <!-- alerts manager -->
              <q-item clickable v-close-popup @click="showAlertsManager">
                <q-item-section>{{ t("filebar.alertsManager") }}</q-item-section>
              </q-item>
              <!-- permissions manager -->
              <q-item clickable v-close-popup @click="showPermissionsManager">
                <q-item-section>{{ t("filebar.permissionsManager") }}</q-item-section>
              </q-item>
              <!-- admin manager -->
              <q-item clickable v-close-popup @click="showAdminManager = true">
                <q-item-section>{{ t("filebar.userAdmin") }}</q-item-section>
              </q-item>
              <!-- core settings -->
              <q-item
                clickable
                v-close-popup
                @click="showEditCoreSettingsModal = true"
              >
                <q-item-section>{{ t("filebar.globalSettings") }}</q-item-section>
              </q-item>
              <!-- code sign -->
              <q-item
                v-if="!hosted"
                clickable
                v-close-popup
                @click="showCodeSign = true"
              >
                <q-item-section>{{ t("filebar.codeSigning") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- tools -->
        <q-btn size="md" dense no-caps flat :label="t('filebar.tools')">
          <q-menu auto-close>
            <q-list dense style="min-width: 240px">
              <q-item
                clickable
                v-close-popup
                @click="showFleetCLIModal = true"
              >
                <q-item-section side>
                  <q-icon name="terminal" size="xs" color="primary" />
                </q-item-section>
                <q-item-section>Central CLI &amp; Modo Compatibilidade Bancária (&gt;_)</q-item-section>
              </q-item>
              <q-separator />
              <!-- bulk command -->
              <q-item
                clickable
                v-close-popup
                @click="showBulkAction('command')"
              >
                <q-item-section>{{ t("filebar.bulkCommand") }}</q-item-section>
              </q-item>
              <!-- bulk script -->
              <q-item clickable v-close-popup @click="showBulkAction('script')">
                <q-item-section>{{ t("filebar.bulkScript") }}</q-item-section>
              </q-item>
              <!-- bulk patch management -->
              <q-item clickable v-close-popup @click="showBulkAction('patch')">
                <q-item-section>{{ t("filebar.bulkPatch") }}</q-item-section>
              </q-item>
              <!-- server maintenance -->
              <q-item
                clickable
                v-close-popup
                @click="showServerMaintenance = true"
              >
                <q-item-section>{{ t("filebar.serverMaintenance") }}</q-item-section>
              </q-item>
              <!-- clear cache -->
              <q-item clickable v-close-popup @click="clearCache">
                <q-item-section>{{ t("filebar.clearCache") }}</q-item-section>
              </q-item>
              <!-- bulk recover agents -->
              <q-item clickable v-close-popup @click="bulkRecoverAgents">
                <q-item-section>{{ t("filebar.recoverAllAgents") }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
        <!-- reports -->
        <q-btn size="md" dense no-caps flat :label="t('filebar.reporting')">
          <q-menu auto-close class="trmm-popover-menu" :offset="[0, 4]">
            <div class="trmm-reports-menu">
              <div
                class="trmm-rm-header row items-center no-wrap q-px-md q-py-xs"
                :class="$q.dark.isActive ? 'trmm-rm-header--dark' : 'trmm-rm-header--light'"
              >
                <q-icon name="assessment" size="16px" color="primary" class="q-mr-xs" />
                <span class="text-caption text-weight-bold">Central de Relatórios &amp; Auditoria</span>
              </div>

              <q-list dense class="q-py-xs">
                <div class="trmm-rm-section">Inventário &amp; Gestão Executiva</div>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('all')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--blue">
                      <q-icon name="assessment" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Central de Relatórios &amp; Inventário Geral</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Todos os equipamentos por empresa/unidade (Excel &amp; PDF)</q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('unit_summary')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--indigo">
                      <q-icon name="apartment" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Resumo Executivo por Empresa &amp; Unidade</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Totais consolidados de agentes, rede, médicos, AD e patrimônio</q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="showInventoryManagerModal = true"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--teal">
                      <q-icon name="inventory_2" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Inventário, Patrimônio &amp; Ativos/Passivos</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Cadastro, tombamento, importação CSV e equipamentos sem agente</q-item-label>
                  </q-item-section>
                </q-item>

                <q-separator class="q-my-xs trmm-rm-sep" />
                <div class="trmm-rm-section">Conformidade, Saúde &amp; Operação</div>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('ad_compliance')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--emerald">
                      <q-icon name="domain" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Relatório Active Directory (AD vs. Workgroup)</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Conformidade real de estações e servidores (sem rede/impressoras)</q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('outside_ad')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--amber">
                      <q-icon name="domain_disabled" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Relatório Computadores Fora do AD</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Somente computadores/servidores Windows fora do domínio</q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('patches_reboot')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--sky">
                      <q-icon name="system_update_alt" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Relatório Patches &amp; Reboot Pendente</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Agentes monitorados com atualizações ou reinicialização pendente</q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('health_checks')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--red">
                      <q-icon name="health_and_safety" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Relatório Saúde &amp; Verificações com Falha</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Agentes com checks falhando ou alertas críticos</q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  clickable
                  v-ripple
                  v-close-popup
                  class="trmm-rm-item"
                  @click="openFleetReports('offline_audit')"
                >
                  <q-item-section side>
                    <div class="trmm-rm-icon trmm-rm-icon--orange">
                      <q-icon name="cloud_off" size="15px" />
                    </div>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">Relatório Computadores Offline / Vencidos</q-item-label>
                    <q-item-label caption class="trmm-rm-caption">Apenas agentes Tactical desconectados (sem falsos positivos)</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </q-menu>
        </q-btn>
        <!-- help -->
        <q-btn v-if="!hosted" size="md" dense no-caps flat :label="t('filebar.help')">
          <q-menu auto-close>
            <q-list dense style="min-width: 100px">
              <q-item clickable v-close-popup @click="openHelp('docs')">
                <q-item-section>Documentation</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="openHelp('github')">
                <q-item-section>GitHub Repo</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="openHelp('bug')">
                <q-item-section>Bug Report</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="openHelp('feature')">
                <q-item-section>Feature Request</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="openHelp('discord')">
                <q-item-section>Join Discord</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </q-btn-group>
      <q-space />
      <!-- edit core settings modal -->
      <q-dialog v-model="showEditCoreSettingsModal">
        <EditCoreSettings @close="showEditCoreSettingsModal = false" />
      </q-dialog>
      <!-- Install Agents -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showInstallAgent">
          <InstallAgent @close="showInstallAgent = false" />
        </q-dialog>
      </div>
      <!-- Update Agents Modal -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog
          v-model="showUpdateAgentsModal"
          maximized
          transition-show="slide-up"
          transition-hide="slide-down"
        >
          <UpdateAgents @close="showUpdateAgentsModal = false" />
        </q-dialog>
      </div>
      <!-- Admin Manager -->
      <div class="q-pa-md q-gutter-sm">
        <q-dialog v-model="showAdminManager">
          <AdminManager @close="showAdminManager = false" />
        </q-dialog>
      </div>
      <!-- Server Maintenance -->
      <q-dialog v-model="showServerMaintenance">
        <ServerMaintenance @close="showMaintenance = false" />
      </q-dialog>
      <!-- Code Sign -->
      <q-dialog v-model="showCodeSign">
        <CodeSign @close="showCodeSign = false" />
      </q-dialog>
      <!-- Fleet Reports Modal -->
      <q-dialog
        v-model="showFleetReportsModal"
        maximized
        transition-show="slide-up"
        transition-hide="slide-down"
      >
        <FleetReportsModal
          :initialReportType="fleetReportType"
          @close="showFleetReportsModal = false"
        />
      </q-dialog>
      <!-- Fleet CLI Modal -->
      <q-dialog v-model="showFleetCLIModal">
        <FleetServerCLIModal @close="showFleetCLIModal = false" />
      </q-dialog>
      <!-- AD Directory Audit Modal -->
      <q-dialog v-model="showADDirectoryAuditModal">
        <ADDirectoryAuditModal @close="showADDirectoryAuditModal = false" />
      </q-dialog>
      <!-- Inventory & Patrimonio Modal -->
      <q-dialog
        v-model="showInventoryManagerModal"
        maximized
        transition-show="slide-up"
        transition-hide="slide-down"
      >
        <InventoryManagerModal @close="showInventoryManagerModal = false" />
      </q-dialog>
    </q-bar>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import DialogWrapper from "@/components/ui/DialogWrapper.vue";
import DebugLog from "@/components/logs/DebugLog.vue";
import PendingActions from "@/components/logs/PendingActions.vue";
import ClientsManager from "@/components/clients/ClientsManager.vue";
import ClientsForm from "@/components/clients/ClientsForm.vue";
import SitesForm from "@/components/clients/SitesForm.vue";
import UpdateAgents from "@/components/modals/agents/UpdateAgents.vue";
import ScriptManager from "@/components/scripts/ScriptManager.vue";
import EditCoreSettings from "@/components/modals/coresettings/EditCoreSettings.vue";
import AlertsManager from "@/components/AlertsManager.vue";
import AutomationManager from "@/components/automation/AutomationManager.vue";
import AdminManager from "@/components/AdminManager.vue";
import InstallAgent from "@/components/modals/agents/InstallAgent.vue";
import AuditManager from "@/components/logs/AuditManager.vue";
import BulkAction from "@/components/modals/agents/BulkAction.vue";
import DeploymentTable from "@/components/clients/DeploymentTable.vue";
import ServerMaintenance from "@/components/modals/core/ServerMaintenance.vue";
import CodeSign from "@/components/modals/coresettings/CodeSign.vue";
import PermissionsManager from "@/components/accounts/PermissionsManager.vue";
import FleetReportsModal from "@/components/modals/reports/FleetReportsModal.vue";
import FleetServerCLIModal from "@/components/modals/core/FleetServerCLIModal.vue";
import ADDirectoryAuditModal from "@/components/modals/agents/ADDirectoryAuditModal.vue";
import InventoryManagerModal from "@/components/modals/agents/InventoryManagerModal.vue";
import { t } from "@/i18n";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { notifyWarning } from "@/utils/notify";

export default {
  name: "FileBar",
  mixins: [mixins],
  components: {
    UpdateAgents,
    EditCoreSettings,
    InstallAgent,
    AdminManager,
    ServerMaintenance,
    CodeSign,
    FleetReportsModal,
    FleetServerCLIModal,
    ADDirectoryAuditModal,
    InventoryManagerModal,
  },
  data() {
    return {
      showServerMaintenance: false,
      showUpdateAgentsModal: false,
      showEditCoreSettingsModal: false,
      showAdminManager: false,
      showInstallAgent: false,
      showCodeSign: false,
      showFleetReportsModal: false,
      showFleetCLIModal: false,
      showADDirectoryAuditModal: false,
      showInventoryManagerModal: false,
      fleetReportType: "all",
    };
  },
  computed: {
    hosted() {
      return this.$store.state.hosted;
    },
  },
  methods: {
    t,
    openFleetReports(reportType = "all") {
      this.fleetReportType = reportType;
      this.showFleetReportsModal = true;
    },
    clearCache() {
      this.$axios
        .get("/core/clearcache/")
        .then((r) => this.notifySuccess(r.data));
    },
    bulkRecoverAgents() {
      this.$q
        .dialog({
          title: "Bulk Recover All Agents?",
          message:
            "This will attempt to reinstall/repair the Tactical and Mesh Agents on all endpoints.",
          cancel: true,
        })
        .onOk(() => {
          this.$axios
            .get("/agents/bulkrecovery/")
            .then((r) => this.notifySuccess(r.data));
        });
    },
    openHelp(mode) {
      let url;
      switch (mode) {
        case "github":
          url = "https://github.com/amidaware/tacticalrmm/";
          break;
        case "docs":
          url = "https://docs.tacticalrmm.com";
          break;
        case "bug":
          url =
            "https://github.com/amidaware/tacticalrmm/issues/new?template=bug_report.md";
          break;
        case "feature":
          url =
            "https://github.com/amidaware/tacticalrmm/issues/new?template=feature_request.md";
          break;
        case "discord":
          url = "https://discord.gg/upGTkWp";
          break;
      }
      window.open(url, "_blank");
    },
    showAutomationManager() {
      this.$q.dialog({
        component: AutomationManager,
      });
    },
    showAlertsManager() {
      this.$q.dialog({
        component: AlertsManager,
      });
    },
    showClientsManager() {
      this.$q
        .dialog({
          component: ClientsManager,
        })
        .onDismiss(() => this.$store.dispatch("refreshDashboard", true));
    },
    showAddClientModal() {
      this.$q
        .dialog({
          component: ClientsForm,
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showAddSiteModal() {
      this.$q
        .dialog({
          component: SitesForm,
        })
        .onOk(() => this.$store.dispatch("loadTree"));
    },
    showPermissionsManager() {
      this.$q.dialog({
        component: PermissionsManager,
      });
    },
    showAuditManager() {
      this.$q.dialog({
        component: DialogWrapper,
        componentProps: {
          vuecomponent: AuditManager,
          noCard: true,
          componentProps: {
            modal: true,
          },
          dialogProps: {
            maximized: true,
            ["transition-show"]: "slide-up",
            ["transition-hide"]: "slide-down",
          },
        },
      });
    },
    showScriptManager() {
      this.$q.dialog({
        component: ScriptManager,
      });
    },
    showBulkAction(mode) {
      this.$q.dialog({
        component: BulkAction,
        componentProps: {
          mode: mode,
        },
      });
    },
    showDebugLog() {
      this.$q.dialog({
        component: DialogWrapper,
        componentProps: {
          vuecomponent: DebugLog,
          noCard: true,
          componentProps: {
            modal: true,
          },
          dialogProps: {
            maximized: true,
            ["transition-show"]: "slide-up",
            ["transition-hide"]: "slide-down",
          },
        },
      });
    },
    showPendingActions() {
      this.$q.dialog({
        component: PendingActions,
      });
    },
    showDeployments() {
      this.$q.dialog({
        component: DeploymentTable,
      });
    },
    showReportsManager() {
      this.$q.dialog({
        component: ReportsManager,
      });
    },
  },
};
</script>

<style scoped>
.trmm-reports-menu {
  min-width: 365px;
  max-width: 92vw;
}

.trmm-rm-header {
  min-height: 36px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-rm-header--dark {
  background: rgba(15, 23, 42, 0.65);
}

.trmm-rm-header--light {
  background: #f1f5f9;
}

.trmm-rm-section {
  padding: 6px 12px 3px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
}

body.body--light .trmm-rm-section {
  color: #64748b;
}

.trmm-rm-item {
  min-height: 44px !important;
  margin: 2px 6px;
  padding: 4px 8px !important;
  border-radius: 8px;
  transition: background-color 0.13s ease;
}

.trmm-rm-item:hover {
  background: rgba(148, 163, 184, 0.14);
}

.trmm-rm-caption {
  font-size: 11px !important;
  opacity: 0.78;
}

.trmm-rm-sep {
  opacity: 0.45;
  margin-left: 10px;
  margin-right: 10px;
}

.trmm-rm-icon {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.trmm-rm-icon--blue {
  background: rgba(59, 130, 246, 0.18);
  color: #60a5fa;
}

.trmm-rm-icon--indigo {
  background: rgba(99, 102, 241, 0.18);
  color: #818cf8;
}

.trmm-rm-icon--teal {
  background: rgba(20, 184, 166, 0.18);
  color: #2dd4bf;
}

.trmm-rm-icon--emerald {
  background: rgba(34, 197, 94, 0.18);
  color: #4ade80;
}

.trmm-rm-icon--amber {
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
}

.trmm-rm-icon--sky {
  background: rgba(14, 165, 233, 0.18);
  color: #38bdf8;
}

.trmm-rm-icon--red {
  background: rgba(239, 68, 68, 0.18);
  color: #f87171;
}

.trmm-rm-icon--orange {
  background: rgba(249, 115, 22, 0.18);
  color: #fb923c;
}

body.body--light .trmm-rm-icon--blue { color: #2563eb; }
body.body--light .trmm-rm-icon--indigo { color: #4f46e5; }
body.body--light .trmm-rm-icon--teal { color: #0f766e; }
body.body--light .trmm-rm-icon--emerald { color: #15803d; }
body.body--light .trmm-rm-icon--amber { color: #b45309; }
body.body--light .trmm-rm-icon--sky { color: #0284c7; }
body.body--light .trmm-rm-icon--red { color: #dc2626; }
body.body--light .trmm-rm-icon--orange { color: #c2410c; }
</style>
