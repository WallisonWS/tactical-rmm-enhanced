<template>
  <div v-if="!selectedAgent" class="q-pa-sm">{{ t("common.noAgentSelected") }}</div>
  <div v-else class="q-pa-sm">
    <q-bar dense style="background-color: transparent">
      <q-btn
        dense
        flat
        icon="security"
        :label="t('sec.runAudit')"
        no-caps
        :loading="loading"
        @click="runAudit"
      />
      <q-btn
        dense
        flat
        icon="list_alt"
        :label="t('sec.inspectAutoruns')"
        no-caps
        :loading="loadingExtra"
        @click="loadStartups"
      />
      <q-btn
        dense
        flat
        icon="group"
        :label="t('sec.auditUsers')"
        no-caps
        :loading="loadingExtra"
        @click="loadUsers"
      />
      <q-space />
      <q-badge
        v-if="audit"
        :color="audit.security_score >= 80 ? 'positive' : audit.security_score >= 55 ? 'warning' : 'negative'"
        class="q-pa-xs text-weight-bold"
      >
        {{ t("sec.score") }}: {{ audit.security_score }} / 100
      </q-badge>
    </q-bar>
    <q-separator class="q-my-xs" />

    <div v-if="audit" class="row q-col-gutter-md q-mt-xs">
      <!-- Posture Controls -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              {{ t("sec.postureTitle") }}
            </div>
            <q-list dense separator>
              <q-item>
                <q-item-section>Antivirus / EDR</q-item-section>
                <q-item-section side>
                  <q-badge :color="audit.antivirus_enabled ? 'positive' : 'negative'">
                    {{ audit.antivirus_enabled ? audit.antivirus_name || "Active" : "Disabled" }}
                  </q-badge>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>Real-Time Protection</q-item-section>
                <q-item-section side>
                  <q-badge :color="audit.realtime_protection ? 'positive' : 'negative'">
                    {{ audit.realtime_protection ? "Enabled" : "Disabled" }}
                  </q-badge>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>Host Firewall</q-item-section>
                <q-item-section side>
                  <q-badge :color="audit.firewall_enabled ? 'positive' : 'negative'">
                    {{ audit.firewall_enabled ? "All Profiles Active" : "Partially/Fully Disabled" }}
                  </q-badge>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>Full Disk Encryption</q-item-section>
                <q-item-section side>
                  <q-badge :color="audit.disk_encrypted ? 'positive' : 'warning'">
                    {{ audit.encryption_detail || (audit.disk_encrypted ? "Encrypted" : "Unencrypted") }}
                  </q-badge>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>User Account Control (UAC)</q-item-section>
                <q-item-section side>
                  <q-badge :color="audit.uac_enabled ? 'positive' : 'negative'">
                    {{ audit.uac_enabled ? "Enabled" : "Disabled" }}
                  </q-badge>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>SMBv1 Legacy Protocol</q-item-section>
                <q-item-section side>
                  <q-badge :color="!audit.smbv1_enabled ? 'positive' : 'negative'">
                    {{ audit.smbv1_enabled ? "Vulnerable (Enabled)" : "Safe (Disabled)" }}
                  </q-badge>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <!-- Firewall Manager -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              {{ t("sec.fwTitle") }}
            </div>
            <div class="row q-gutter-xs q-mb-md">
              <q-btn
                dense
                unelevated
                color="positive"
                :label="t('sec.enableAllFw')"
                no-caps
                size="sm"
                @click="applyFirewallAction('enable_all')"
              />
              <q-btn
                dense
                outline
                color="negative"
                :label="t('sec.disableAllFw')"
                no-caps
                size="sm"
                @click="applyFirewallAction('disable_all')"
              />
            </div>

            <div class="row q-col-gutter-xs items-center">
              <div class="col-4">
                <q-input v-model="fwPort" dense outlined label="Port (e.g. 445)" />
              </div>
              <div class="col-4">
                <q-select
                  v-model="fwProto"
                  :options="['TCP', 'UDP']"
                  dense
                  outlined
                  label="Protocol"
                />
              </div>
              <div class="col-4">
                <q-btn
                  dense
                  unelevated
                  color="negative"
                  :label="t('sec.blockPort')"
                  no-caps
                  class="full-width"
                  @click="applyFirewallAction('block_port')"
                />
              </div>
            </div>

            <q-separator class="q-my-sm" />
            <div class="text-caption text-weight-bold q-mb-xs">
              {{ t("sec.recommendations") }}
            </div>
            <q-list dense>
              <q-item v-for="(rec, i) in audit.recommendations" :key="i">
                <q-item-section avatar>
                  <q-icon name="verified_user" color="primary" size="xs" />
                </q-item-section>
                <q-item-section class="text-caption">{{ rec }}</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <!-- Autoruns / Users / Administrators -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              Local Administrators ({{ audit.local_admins?.length || 0 }}) &amp; Startup ({{ audit.startup_items_count }})
            </div>
            <div class="q-gutter-xs q-mb-sm">
              <q-chip
                v-for="adm in audit.local_admins"
                :key="adm"
                dense
                icon="admin_panel_settings"
                color="primary"
                text-color="white"
              >
                {{ adm }}
              </q-chip>
            </div>

            <div v-if="startupItems.length">
              <div class="text-caption text-weight-bold q-mb-xs">Autorun Entries</div>
              <q-list dense bordered separator style="max-height: 160px" class="scroll">
                <q-item v-for="(st, idx) in startupItems" :key="idx">
                  <q-item-section>
                    <q-item-label class="text-weight-bold">{{ st.name }}</q-item-label>
                    <q-item-label caption>{{ st.command }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>

            <div v-if="localUsers.length" class="q-mt-sm">
              <div class="text-caption text-weight-bold q-mb-xs">Local Accounts</div>
              <q-list dense bordered separator style="max-height: 160px" class="scroll">
                <q-item v-for="(u, idx) in localUsers" :key="idx">
                  <q-item-section>
                    <q-item-label>{{ u.username }}</q-item-label>
                    <q-item-label caption>Last logon: {{ u.last_logon }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-badge :color="u.is_admin ? 'warning' : 'grey'">
                      {{ u.is_admin ? "Admin" : "Standard" }}
                    </q-badge>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import {
  fetchAgentSecurityAudit,
  queryAgentSecurityDetails,
  executeAgentFirewallRule,
  type SecurityAuditReport,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";
import { useI18n } from "@/i18n";

const { t } = useI18n();
const store = useStore();
const selectedAgent = computed(() => store.state.selectedRow);
const loading = ref(false);
const loadingExtra = ref(false);
const audit = ref<SecurityAuditReport | null>(null);
const startupItems = ref<any[]>([]);
const localUsers = ref<any[]>([]);
const fwPort = ref("445");
const fwProto = ref<"TCP" | "UDP">("TCP");

async function runAudit() {
  if (!selectedAgent.value) return;
  loading.value = true;
  try {
    audit.value = await fetchAgentSecurityAudit(selectedAgent.value);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to run security audit");
  } finally {
    loading.value = false;
  }
}

async function loadStartups() {
  if (!selectedAgent.value) return;
  loadingExtra.value = true;
  try {
    startupItems.value = await queryAgentSecurityDetails(selectedAgent.value, "startup_items");
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to query startup items");
  } finally {
    loadingExtra.value = false;
  }
}

async function loadUsers() {
  if (!selectedAgent.value) return;
  loadingExtra.value = true;
  try {
    localUsers.value = await queryAgentSecurityDetails(selectedAgent.value, "local_users");
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to query local users");
  } finally {
    loadingExtra.value = false;
  }
}

async function applyFirewallAction(action: "enable_all" | "disable_all" | "block_port") {
  if (!selectedAgent.value) return;
  try {
    await executeAgentFirewallRule(selectedAgent.value, {
      action,
      port: fwPort.value,
      protocol: fwProto.value,
      direction: "in",
    });
    notifySuccess(`Firewall action '${action}' applied`);
    await runAudit();
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to apply firewall rule");
  }
}

watch(selectedAgent, () => {
  audit.value = null;
  startupItems.value = [];
  localUsers.value = [];
  if (selectedAgent.value) runAudit();
});

onMounted(() => {
  if (selectedAgent.value) runAudit();
});
</script>
