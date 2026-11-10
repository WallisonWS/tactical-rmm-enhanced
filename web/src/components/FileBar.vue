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
            <q-list dense style="min-width: 100px">
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
          <q-menu auto-close>
            <q-list dense style="min-width: 240px">
              <q-item
                clickable
                v-close-popup
                @click="openFleetReports('all')"
              >
                <q-item-section side>
                  <q-icon name="assessment" size="xs" color="primary" />
                </q-item-section>
                <q-item-section>Central de Relatórios &amp; Inventário Geral</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="openFleetReports('ad_compliance')"
              >
                <q-item-section side>
                  <q-icon name="domain" size="xs" color="teal-5" />
                </q-item-section>
                <q-item-section>Relatório Active Directory (AD vs. Workgroup)</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="openFleetReports('outside_ad')"
              >
                <q-item-section side>
                  <q-icon name="domain_disabled" size="xs" color="amber-8" />
                </q-item-section>
                <q-item-section>Relatório Computadores Fora do AD</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="openFleetReports('patches_reboot')"
              >
                <q-item-section side>
                  <q-icon name="system_update" size="xs" color="info" />
                </q-item-section>
                <q-item-section>Relatório Patches &amp; Reboot Pendente</q-item-section>
              </q-item>
              <q-item
                clickable
                v-close-popup
                @click="openFleetReports('offline_audit')"
              >
                <q-item-section side>
                  <q-icon name="cloud_off" size="xs" color="warning" />
                </q-item-section>
                <q-item-section>Relatório Computadores Offline / Vencidos</q-item-section>
              </q-item>
            </q-list>
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
