<template>
  <div class="q-px-sm q-pt-xs q-pb-sm">
    <div class="row q-col-gutter-sm items-stretch">
      <!-- Fleet Health Score -->
      <div class="col-12 col-sm-6 col-md-2">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-pa-sm row items-center no-wrap">
            <q-circular-progress
              show-value
              font-size="12px"
              :value="summary.fleet_health_score"
              size="44px"
              :thickness="0.22"
              :color="scoreColor(summary.fleet_health_score)"
              track-color="grey-8"
              class="q-mr-sm text-weight-bold"
            >
              {{ summary.fleet_health_score }}%
            </q-circular-progress>
            <div>
              <div class="text-caption text-grey">{{ t("kpi.fleetHealth") }}</div>
              <div class="text-subtitle2 text-weight-bold">
                {{ summary.online_agents }} / {{ summary.total_agents }} {{ t("kpi.onlineAgents") }}
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Availability % -->
      <div class="col-12 col-sm-6 col-md-2">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between">
              <span class="text-caption text-grey">{{ t("kpi.availability") }}</span>
              <q-icon name="fas fa-signal" color="positive" size="xs" />
            </div>
            <div class="text-h6 text-weight-bold">
              {{ summary.availability_percent }}%
            </div>
            <div class="text-caption">
              <span class="text-warning">{{ summary.offline_agents }} {{ t("nav.offline") }}</span>
              &bull;
              <span class="text-negative">{{ summary.overdue_agents }} overdue</span>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Patch Compliance -->
      <div class="col-12 col-sm-6 col-md-2">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between">
              <span class="text-caption text-grey">{{ t("kpi.patchCompliance") }}</span>
              <q-icon name="system_update" color="primary" size="xs" />
            </div>
            <div class="text-h6 text-weight-bold">
              {{ summary.patch_compliance_percent }}%
            </div>
            <div class="text-caption text-grey">
              {{ summary.agents_with_pending_patches }} {{ t("kpi.pendingAgents") }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Active Alerts & Failing Checks -->
      <div class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between">
              <span class="text-caption text-grey">{{ t("kpi.activeAlerts") }}</span>
              <q-icon name="notifications_active" color="warning" size="xs" />
            </div>
            <div class="row items-center q-gutter-x-sm q-mt-xs">
              <q-badge color="negative" class="q-pa-xs">
                {{ summary.active_alerts.error }} {{ t("kpi.critical") }}
              </q-badge>
              <q-badge color="warning" text-color="black" class="q-pa-xs">
                {{ summary.active_alerts.warning }} {{ t("kpi.warnings") }}
              </q-badge>
              <q-badge color="deep-orange" class="q-pa-xs">
                {{ summary.failing_checks_count }} {{ t("kpi.failingChecks") }}
              </q-badge>
            </div>
            <div class="text-caption text-grey q-mt-xs">
              {{ summary.reboot_needed_agents }} {{ t("kpi.pendingReboots") }} &bull;
              {{ summary.maintenance_agents }} {{ t("kpi.inMaintenance") }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Quick Fleet Actions -->
      <div class="col-12 col-md-3">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-pa-sm flex items-center justify-between full-height">
            <div>
              <div class="text-caption text-grey">Autonomous Operations</div>
              <div class="text-subtitle2 text-weight-bold">RMM Pro Engine</div>
            </div>
            <div class="row q-gutter-xs">
              <q-btn
                dense
                unelevated
                color="primary"
                icon="refresh"
                :label="t('kpi.refreshKpis')"
                no-caps
                size="sm"
                :loading="loading"
                @click="loadSummary"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchFleetExecutiveSummary, type FleetExecutiveSummary } from "@/api/enhanced";
import { useI18n } from "@/i18n";

const { t } = useI18n();
const loading = ref(false);
const summary = ref<FleetExecutiveSummary>({
  total_agents: 0,
  online_agents: 0,
  offline_agents: 0,
  overdue_agents: 0,
  reboot_needed_agents: 0,
  maintenance_agents: 0,
  availability_percent: 100,
  patch_compliance_percent: 100,
  fleet_health_score: 100,
  active_alerts: { total: 0, error: 0, warning: 0 },
  failing_checks_count: 0,
  agents_with_pending_patches: 0,
  timestamp: "",
});

function scoreColor(score: number): string {
  if (score >= 85) return "positive";
  if (score >= 65) return "warning";
  return "negative";
}

async function loadSummary() {
  loading.value = true;
  try {
    summary.value = await fetchFleetExecutiveSummary();
  } catch (e) {
    // Keep fallback defaults if endpoint not yet populated
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadSummary();
});
</script>
