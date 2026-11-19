<template>
  <div v-if="!selectedAgent" class="q-pa-md text-grey-6 row items-center q-gutter-x-sm">
    <q-icon name="space_dashboard" size="20px" />
    <span>Nenhum agente selecionado</span>
  </div>
  <div v-else-if="!summary && loading" class="q-pa-md flex flex-center">
    <q-circular-progress
      indeterminate
      size="44px"
      color="primary"
      class="q-ma-md"
    />
  </div>
  <div v-else-if="summary" class="trmm-summary-root q-pa-sm q-pb-md">
    <!-- Executive Agent Action Header -->
    <div
      class="trmm-summary-header row items-center justify-between wrap q-px-md q-py-xs q-mb-sm"
      :class="$q.dark.isActive ? 'trmm-summary-card--dark' : 'trmm-summary-card--light'"
    >
      <div
        class="row items-center wrap col-grow"
        style="min-width: 240px; gap: 6px 8px"
      >
        <q-btn
          dense
          flat
          round
          size="sm"
          icon="refresh"
          color="primary"
          @click="refreshSummary"
        >
          <q-tooltip>Atualizar dados e WMI do equipamento</q-tooltip>
        </q-btn>

        <div
          class="trmm-status-pill row items-center no-wrap"
          :class="
            summary.status === 'overdue'
              ? 'trmm-status-pill--negative'
              : summary.status === 'offline'
                ? 'trmm-status-pill--warning'
                : 'trmm-status-pill--positive'
          "
        >
          <span class="trmm-status-dot-sm q-mr-xs" />
          <q-icon name="signal_cellular_alt" size="14px" />
          <q-tooltip>
            {{
              summary.status === "overdue"
                ? "Agente vencido (Overdue)"
                : store.getters.formatDate(summary.last_seen)
            }}
          </q-tooltip>
        </div>

        <span class="text-subtitle2 text-weight-bold" style="letter-spacing: 0.01em">
          {{ summary.hostname }}
        </span>

        <q-badge
          v-if="summary.client_name"
          :color="getEntityBadgeColor(summary.client_name)"
          text-color="white"
          class="text-weight-bold q-px-sm"
          style="border-radius: 6px; padding-top: 3px; padding-bottom: 3px"
        >
          Empresa: {{ summary.client_name }}
        </q-badge>
        <q-badge
          v-if="summary.site_name"
          outline
          :color="getEntityBadgeColor(summary.site_name)"
          class="text-weight-bold q-px-sm"
          style="border-radius: 6px; padding-top: 2px; padding-bottom: 2px"
        >
          Unidade: {{ summary.site_name }}
        </q-badge>
        <q-badge
          v-if="isAgentlessAsset"
          color="blue-grey-7"
          text-color="white"
          class="text-weight-medium q-px-sm"
          style="border-radius: 6px"
        >
          Inventário LAN (Sem Agente)
        </q-badge>
        <q-badge
          v-if="summary.maintenance_mode"
          color="positive"
          text-color="white"
          class="text-weight-medium q-px-sm"
          style="border-radius: 6px"
        >
          Modo de Manutenção
        </q-badge>

        <span class="text-caption" :class="$q.dark.isActive ? 'text-grey-4' : 'text-grey-7'">
          &bull; {{ summary.operating_system }}
          <template v-if="summary.version && !isAgentlessAsset">
            &bull; Agent v{{ summary.version }}
          </template>
        </span>
      </div>

      <div class="row items-center wrap" style="gap: 6px">
        <q-btn
          v-if="!isAgentlessAsset"
          dense
          unelevated
          no-wrap
          color="primary"
          label="Take Control"
          icon="connected_tv"
          size="sm"
          no-caps
          class="trmm-sum-btn trmm-sum-btn--primary"
          @click="runTakeControl(selectedAgent)"
        />
        <q-btn
          v-else
          dense
          unelevated
          no-wrap
          color="teal-7"
          label="Editar Patrimônio / Setor"
          icon="qr_code_2"
          size="sm"
          no-caps
          class="trmm-sum-btn trmm-sum-btn--primary"
          @click="openPatrimonioDialog"
        />
        <q-btn
          v-if="!isAgentlessAsset"
          dense
          flat
          no-wrap
          label="Remote Background"
          icon="terminal"
          size="sm"
          no-caps
          class="trmm-sum-btn trmm-sum-btn--ghost"
          @click="runRemoteBackground(selectedAgent, summary.plat)"
        />
        <q-btn
          v-if="summary.plat === 'windows'"
          dense
          flat
          no-wrap
          label="Conectar RDP (.rdp)"
          icon="cast_connected"
          size="sm"
          no-caps
          class="trmm-sum-btn trmm-sum-btn--ghost"
          :loading="rdpConnecting"
          @click="connectNativeRDP"
        />
        <q-btn
          v-if="!isAgentlessAsset && summary.plat === 'windows' && !adDomainInfo.inDomain"
          dense
          unelevated
          no-wrap
          color="amber-9"
          label="Ingressar no AD"
          icon="domain_add"
          size="sm"
          no-caps
          class="trmm-sum-btn"
          @click="showJoinAdDialog = true"
        />
        <q-btn
          dense
          flat
          no-wrap
          label="Popout"
          icon="open_in_new"
          size="sm"
          no-caps
          class="trmm-sum-btn trmm-sum-btn--ghost"
          @click="openAgentWindow(selectedAgent)"
        />
        <q-btn-dropdown
          dense
          flat
          no-wrap
          size="sm"
          no-caps
          icon="bolt"
          label="Actions"
          content-class="trmm-popover-menu"
          class="trmm-sum-btn trmm-sum-btn--ghost"
        >
          <AgentActionMenu :agent="summary" />
        </q-btn-dropdown>
      </div>
    </div>

    <!-- 3 Structured Executive Info Cards -->
    <div class="row q-col-gutter-sm items-stretch">
      <!-- Card 1: Hardware & Network Details -->
      <div class="col-12 col-md-5 flex">
        <div
          class="trmm-summary-card full-width q-pa-sm"
          :class="$q.dark.isActive ? 'trmm-summary-card--dark' : 'trmm-summary-card--light'"
        >
          <div class="trmm-card-title row items-center q-mb-xs">
            <div class="trmm-section-icon trmm-section-icon--blue q-mr-xs">
              <q-icon name="computer" size="15px" />
            </div>
            <span>Hardware Details</span>
          </div>

          <div class="trmm-spec-list">
            <div class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--blue">
                <q-icon name="devices" size="15px" />
              </div>
              <div class="trmm-spec-body">
                <div class="trmm-spec-label">Modelo / Fabricante</div>
                <div class="trmm-spec-value">{{ displayMakeModel || "—" }}</div>
              </div>
            </div>

            <div class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--indigo">
                <q-icon name="memory" size="15px" />
              </div>
              <div class="trmm-spec-body">
                <div class="trmm-spec-label">
                  {{ isAgentlessAsset ? "Função / Descrição" : "Processador (CPU)" }}
                </div>
                <div class="trmm-spec-value">{{ displayCpuOrFunction }}</div>
              </div>
            </div>

            <div v-if="summary.total_ram" class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--teal">
                <q-icon name="developer_board" size="15px" />
              </div>
              <div class="trmm-spec-body">
                <div class="trmm-spec-label">Memória RAM</div>
                <div class="trmm-spec-value">{{ summary.total_ram }} GB RAM</div>
              </div>
            </div>
            <div v-else-if="inventoryTag && inventoryTag.asset_subtype" class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--teal">
                <q-icon name="category" size="15px" />
              </div>
              <div class="trmm-spec-body">
                <div class="trmm-spec-label">Subtipo do Ativo</div>
                <div class="trmm-spec-value">{{ inventoryTag.asset_subtype }}</div>
              </div>
            </div>

            <div
              v-for="(disk, i) in summary.physical_disks"
              :key="disk + i"
              class="trmm-spec-row"
            >
              <div class="trmm-spec-icon trmm-spec-icon--slate">
                <q-icon name="storage" size="15px" />
              </div>
              <div class="trmm-spec-body">
                <div class="trmm-spec-label">Disco Físico</div>
                <div class="trmm-spec-value">{{ disk }}</div>
              </div>
            </div>

            <div v-if="showGraphicsRow" class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--purple">
                <q-icon name="monitor" size="15px" />
              </div>
              <div class="trmm-spec-body">
                <div class="trmm-spec-label">Placa Gráfica (GPU)</div>
                <div class="trmm-spec-value">{{ summary.graphics }}</div>
              </div>
            </div>

            <div v-if="serial_number" class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--slate">
                <q-icon name="qr_code" size="15px" />
              </div>
              <div class="trmm-spec-body row items-center justify-between no-wrap">
                <div style="min-width: 0">
                  <div class="trmm-spec-label">Nº de Série / Service Tag</div>
                  <div class="trmm-spec-value trmm-mono">{{ serial_number }}</div>
                </div>
                <q-btn
                  dense
                  flat
                  round
                  size="xs"
                  icon="content_copy"
                  color="grey-5"
                  @click="copySpecValue(serial_number)"
                >
                  <q-tooltip>Copiar Serial</q-tooltip>
                </q-btn>
              </div>
            </div>

            <!-- Patrimônio & Setor -->
            <div class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--teal">
                <q-icon name="qr_code_2" size="15px" />
              </div>
              <div class="trmm-spec-body row items-center justify-between no-wrap">
                <div class="row items-center wrap" style="gap: 4px 8px; min-width: 0">
                  <div class="col-12 trmm-spec-label">Patrimônio &amp; Localização</div>
                  <q-badge
                    v-if="inventoryTag && inventoryTag.patrimonio"
                    color="teal-7"
                    class="text-weight-bold q-px-sm"
                    style="border-radius: 5px"
                  >
                    {{ inventoryTag.patrimonio }}
                  </q-badge>
                  <span v-else class="text-caption text-grey-5">Não definido</span>
                  <span
                    v-if="inventoryTag && inventoryTag.sector_location"
                    class="text-caption text-grey-5"
                  >
                    &bull; Setor: {{ inventoryTag.sector_location }}
                  </span>
                </div>
                <q-btn
                  dense
                  flat
                  size="xs"
                  color="teal-4"
                  icon="edit"
                  label="Editar"
                  no-caps
                  class="q-px-xs"
                  @click="openPatrimonioDialog"
                />
              </div>
            </div>

            <div class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--sky">
                <q-icon name="public" size="15px" />
              </div>
              <div class="trmm-spec-body row items-center justify-between no-wrap">
                <div style="min-width: 0">
                  <div class="trmm-spec-label">Public IP</div>
                  <div class="trmm-spec-value trmm-mono">{{ summary.public_ip || "—" }}</div>
                </div>
                <q-btn
                  v-if="summary.public_ip"
                  dense
                  flat
                  round
                  size="xs"
                  icon="content_copy"
                  color="grey-5"
                  @click="copySpecValue(summary.public_ip)"
                >
                  <q-tooltip>Copiar IP Público</q-tooltip>
                </q-btn>
              </div>
            </div>

            <div class="trmm-spec-row">
              <div class="trmm-spec-icon trmm-spec-icon--emerald">
                <q-icon name="lan" size="15px" />
              </div>
              <div class="trmm-spec-body row items-center justify-between no-wrap">
                <div style="min-width: 0">
                  <div class="trmm-spec-label">LAN IP</div>
                  <div class="trmm-spec-value trmm-mono">{{ summary.local_ips || "—" }}</div>
                </div>
                <q-btn
                  v-if="summary.local_ips"
                  dense
                  flat
                  round
                  size="xs"
                  icon="content_copy"
                  color="grey-5"
                  @click="copySpecValue(summary.local_ips)"
                >
                  <q-tooltip>Copiar IP Local</q-tooltip>
                </q-btn>
              </div>
            </div>

            <div v-if="summary.plat === 'windows'" class="trmm-spec-row">
              <div
                class="trmm-spec-icon"
                :class="adDomainInfo.inDomain ? 'trmm-spec-icon--emerald' : 'trmm-spec-icon--amber'"
              >
                <q-icon :name="adDomainInfo.inDomain ? 'domain' : 'domain_disabled'" size="15px" />
              </div>
              <div class="trmm-spec-body row items-center justify-between no-wrap">
                <div style="min-width: 0">
                  <div class="trmm-spec-label">Active Directory</div>
                  <div v-if="adDomainInfo.inDomain" class="trmm-spec-value">
                    Domínio AD: <b>{{ adDomainInfo.domainName }}</b>
                  </div>
                  <div v-else class="trmm-spec-value text-amber-5">
                    Fora do AD ({{ adDomainInfo.domainName }})
                  </div>
                </div>
                <q-btn
                  v-if="!adDomainInfo.inDomain && !isAgentlessAsset"
                  dense
                  flat
                  size="xs"
                  color="amber-6"
                  icon="domain_add"
                  label="Ingressar no AD"
                  no-caps
                  class="q-px-xs"
                  @click="showJoinAdDialog = true"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Card 2: Checks Status & Custom Fields -->
      <div class="col-12 col-md-3 flex">
        <div
          class="trmm-summary-card full-width q-pa-sm"
          :class="$q.dark.isActive ? 'trmm-summary-card--dark' : 'trmm-summary-card--light'"
        >
          <div class="trmm-card-title row items-center q-mb-sm">
            <div class="trmm-section-icon trmm-section-icon--emerald q-mr-xs">
              <q-icon name="health_and_safety" size="15px" />
            </div>
            <span>Checks Status</span>
          </div>

          <div v-if="summary.checks.total !== 0" class="column q-gutter-y-xs">
            <div
              v-if="summary.checks.passing"
              class="trmm-check-pill trmm-check-pill--positive row items-center no-wrap"
            >
              <q-icon name="check_circle" size="17px" class="q-mr-xs" />
              <span class="text-weight-bold q-mr-xs">{{ summary.checks.passing }}</span>
              <span>checks passing</span>
            </div>
            <div
              v-if="summary.checks.failing"
              class="trmm-check-pill trmm-check-pill--negative row items-center no-wrap"
            >
              <q-icon name="error" size="17px" class="q-mr-xs" />
              <span class="text-weight-bold q-mr-xs">{{ summary.checks.failing }}</span>
              <span>checks failing</span>
            </div>
            <div
              v-if="summary.checks.warning"
              class="trmm-check-pill trmm-check-pill--warning row items-center no-wrap"
            >
              <q-icon name="warning" size="17px" class="q-mr-xs" />
              <span class="text-weight-bold q-mr-xs">{{ summary.checks.warning }}</span>
              <span>checks warning</span>
            </div>
            <div
              v-if="summary.checks.info"
              class="trmm-check-pill trmm-check-pill--info row items-center no-wrap"
            >
              <q-icon name="info" size="17px" class="q-mr-xs" />
              <span class="text-weight-bold q-mr-xs">{{ summary.checks.info }}</span>
              <span>checks info</span>
            </div>
            <div
              v-if="
                summary.checks.total !== 0 &&
                summary.checks.passing === 0 &&
                summary.checks.failing === 0 &&
                summary.checks.warning === 0 &&
                summary.checks.info === 0
              "
              class="text-caption text-grey-5 q-pa-xs"
            >
              {{ summary.checks.total }} checks awaiting first synchronization
            </div>
          </div>
          <div
            v-else
            class="trmm-empty-mini row items-center no-wrap q-pa-sm"
            :class="$q.dark.isActive ? 'trmm-empty-mini--dark' : 'trmm-empty-mini--light'"
          >
            <q-icon name="task_alt" size="18px" color="grey-5" class="q-mr-sm" />
            <span class="text-caption text-grey-5">No checks</span>
          </div>

          <template v-if="customFields.length > 0">
            <q-separator class="q-my-sm" />
            <div class="trmm-card-title row items-center q-mb-xs">
              <div class="trmm-section-icon trmm-section-icon--purple q-mr-xs">
                <q-icon name="tune" size="15px" />
              </div>
              <span>Custom Fields</span>
            </div>
            <div class="column q-gutter-y-xs">
              <div
                v-for="(field, i) in customFields"
                :key="field + i"
                class="trmm-custom-field-row row items-center justify-between q-px-sm q-py-xs"
              >
                <span class="text-caption text-grey-5">{{ field.name }}</span>
                <span class="text-caption text-weight-bold">{{ field.value }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Card 3: Storage / Disks -->
      <div class="col-12 col-md-4 flex">
        <div
          class="trmm-summary-card full-width q-pa-sm"
          :class="$q.dark.isActive ? 'trmm-summary-card--dark' : 'trmm-summary-card--light'"
        >
          <div class="trmm-card-title row items-center q-mb-sm">
            <div class="trmm-section-icon trmm-section-icon--sky q-mr-xs">
              <q-icon name="sd_storage" size="15px" />
            </div>
            <span>Disks</span>
          </div>

          <div v-if="disks.length > 0" class="column q-gutter-y-sm">
            <div
              v-for="disk in disks"
              :key="disk.device"
              class="trmm-disk-card q-pa-sm"
              :class="$q.dark.isActive ? 'trmm-disk-card--dark' : 'trmm-disk-card--light'"
            >
              <div class="row items-center justify-between q-mb-xs">
                <div class="row items-center no-wrap" style="gap: 6px">
                  <q-icon name="storage" size="16px" color="primary" />
                  <span class="text-subtitle2 text-weight-bold">{{ disk.device }}</span>
                  <q-badge
                    :color="$q.dark.isActive ? 'blue-grey-9' : 'blue-grey-1'"
                    :text-color="$q.dark.isActive ? 'grey-4' : 'blue-grey-8'"
                    style="font-size: 10px; border-radius: 5px"
                  >
                    {{ disk.fstype }}
                  </q-badge>
                </div>
                <q-badge
                  rounded
                  :color="diskBarColor(disk.percent)"
                  text-color="white"
                  class="text-weight-bold"
                  style="font-size: 11px; padding: 2px 7px"
                >
                  {{ Math.round(disk.percent) }}%
                </q-badge>
              </div>

              <q-linear-progress
                rounded
                size="10px"
                :value="disk.percent / 100"
                :color="diskBarColor(disk.percent)"
                track-color="grey-8"
                class="q-my-xs"
              />

              <div class="row items-center justify-between text-caption q-mt-xs">
                <span :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                  {{ disk.free }} free of {{ disk.total }}
                </span>
              </div>
            </div>
          </div>
          <div
            v-else
            class="trmm-empty-mini row items-center no-wrap q-pa-sm"
            :class="$q.dark.isActive ? 'trmm-empty-mini--dark' : 'trmm-empty-mini--light'"
          >
            <q-icon name="storage" size="18px" color="grey-5" class="q-mr-sm" />
            <span class="text-caption text-grey-5">
              {{
                isAgentlessAsset
                  ? "Telemetria de disco disponível com Agente Tactical"
                  : "Nenhum volume reportado"
              }}
            </span>
          </div>
        </div>
      </div>
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
            label="Domínio Active Directory (ex: corp.local)"
          />
          <q-input
            v-model="joinAdForm.admin_user"
            dense
            outlined
            label="Usuário Administrador do Domínio (ex: DOMINIO\administrador)"
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
            label="Caminho da OU (Opcional — ex: OU=Computadores,DC=corp,DC=local)"
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

    <!-- Modal: Editar Patrimônio & Localização do Agente -->
    <q-dialog v-model="showPatrimonioDialog" persistent>
      <q-card style="min-width: 440px">
        <q-card-section class="row items-center">
          <q-icon name="qr_code_2" color="teal" size="sm" class="q-mr-sm" />
          <div class="text-subtitle1 text-weight-bold">
            Patrimônio &amp; Setor — {{ summary.hostname }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-y-sm">
          <q-input
            v-model="patrimonioForm.patrimonio"
            dense
            outlined
            autofocus
            label="Nº do Patrimônio / Tombamento"
            placeholder="Ex: PAT-001452"
          />
          <q-input
            v-model="patrimonioForm.sector_location"
            dense
            outlined
            label="Setor / Sala / Unidade"
            placeholder="Ex: Recepção Ceres"
          />
          <q-input
            v-model="patrimonioForm.responsible"
            dense
            outlined
            label="Responsável / Ponto Focal"
          />
          <q-input
            v-model="patrimonioForm.notes"
            type="textarea"
            rows="2"
            dense
            outlined
            label="Observações de Inventário"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="teal-7"
            icon="save"
            label="Salvar Patrimônio"
            :loading="savingPatrimonio"
            @click="submitPatrimonio"
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
import { copyToClipboard } from "quasar";
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
  resolveFirstReachableHost,
  joinAgentToADDomain,
  fetchFleetExecutiveSummary,
  fleetDomainMap,
  fetchAgentInventoryTag,
  saveAgentInventoryTag,
  getEntityBadgeColor,
} from "@/api/enhanced";
import { notifySuccess, notifyError, notifyWarning } from "@/utils/notify";
import { fetchCustomFields } from "@/api/core";

// ui imports
import AgentActionMenu from "@/components/agents/AgentActionMenu.vue";

let _customFieldsCache = null;
let _customFieldsCacheAt = 0;
let _customFieldsInflight = null;
const CUSTOM_FIELDS_TTL_MS = 60_000;

function getCachedCustomFields() {
  const now = Date.now();
  if (_customFieldsCache && now - _customFieldsCacheAt < CUSTOM_FIELDS_TTL_MS) {
    return Promise.resolve(_customFieldsCache);
  }
  if (_customFieldsInflight) return _customFieldsInflight;
  const req = fetchCustomFields()
    .then((res) => {
      _customFieldsCache = res;
      _customFieldsCacheAt = Date.now();
      return res;
    })
    .finally(() => {
      if (_customFieldsInflight === req) _customFieldsInflight = null;
    });
  _customFieldsInflight = req;
  return req;
}

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
    const inventoryTag = ref(null);
    const showPatrimonioDialog = ref(false);
    const savingPatrimonio = ref(false);
    const patrimonioForm = ref({
      patrimonio: "",
      sector_location: "",
      responsible: "",
      notes: "",
    });
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
      let rdpConfirmed = false;
      try {
        await manageAgentRDP(selectedAgent.value, "enable_rdp", false);
        rdpConfirmed = true;
      } catch (e) {
        rdpConfirmed = false;
      } finally {
        rdpConnecting.value = false;
      }
      const firstIp = resolveFirstReachableHost(
        summary.value.local_ips,
        summary.value.hostname,
        summary.value.public_ip,
      );
      downloadNativeRDPFile(summary.value.hostname, firstIp, 3389);
      if (rdpConfirmed) {
        notifySuccess(`Conexão RDP (${firstIp}) habilitada e arquivo ${summary.value.hostname}.rdp baixado!`);
      } else {
        notifyWarning(
          `Agente não respondeu via NATS para habilitar o TermService; arquivo ${summary.value.hostname}.rdp baixado com IP ${firstIp}.`,
        );
      }
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
          await fetchFleetExecutiveSummary(true).catch(() => {});
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
      return summary.value.cpu_model?.[0] || "unknown cpu model";
    });

    const displayMakeModel = computed(() => {
      const tagManuf = (inventoryTag.value?.manufacturer || "").trim();
      const tagModel = (inventoryTag.value?.model_name || "").trim();
      if (tagManuf || tagModel) {
        if (tagModel && tagManuf && tagModel.toLowerCase().startsWith(tagManuf.toLowerCase())) {
          return tagModel;
        }
        return `${tagManuf} ${tagModel}`.trim();
      }
      const wmiManuf = (summary.value?.wmi_detail?.cs_manuf || "").trim();
      const wmiModel = (summary.value?.wmi_detail?.cs_model || "").trim();
      if (wmiManuf || wmiModel) {
        if (wmiModel && wmiManuf && wmiModel.toLowerCase().startsWith(wmiManuf.toLowerCase())) {
          return wmiModel;
        }
        return `${wmiManuf} ${wmiModel}`.trim();
      }
      return summary.value?.make_model || "";
    });

    const displayCpuOrFunction = computed(() => {
      const c = (cpu.value || "").trim();
      if (c && c.toLowerCase() !== "unknown cpu model") {
        return c;
      }
      const exactFn = (summary.value?.wmi_detail?.exact_function || "").trim();
      if (exactFn) {
        return `Função: ${exactFn}`;
      }
      const notes = (inventoryTag.value?.notes || "").trim();
      if (notes) {
        return notes;
      }
      return "Ativo Descoberto na Rede (Inventário)";
    });

    const showGraphicsRow = computed(() => {
      const g = (summary.value?.graphics || "").trim();
      if (!g) return false;
      const lower = g.toLowerCase();
      if (
        lower.includes("requires agent") ||
        lower.includes("error getting graphics")
      ) {
        return false;
      }
      return true;
    });

    const isAgentlessAsset = computed(() => {
      if (inventoryTag.value && inventoryTag.value.has_agent === false) {
        return true;
      }
      const ver = String(summary.value?.version || "").trim();
      const mesh = String(summary.value?.mesh_node_id || "").trim();
      return (ver === "" || ver === "0.1.0") && !mesh;
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

    function openPatrimonioDialog() {
      patrimonioForm.value = {
        patrimonio: inventoryTag.value?.patrimonio || "",
        sector_location: inventoryTag.value?.sector_location || "",
        responsible: inventoryTag.value?.responsible || "",
        notes: inventoryTag.value?.notes || "",
      };
      showPatrimonioDialog.value = true;
    }

    async function submitPatrimonio() {
      if (!selectedAgent.value) return;
      savingPatrimonio.value = true;
      try {
        inventoryTag.value = await saveAgentInventoryTag(selectedAgent.value, {
          patrimonio: patrimonioForm.value.patrimonio.trim(),
          sector_location: patrimonioForm.value.sector_location.trim(),
          responsible: patrimonioForm.value.responsible.trim(),
          notes: patrimonioForm.value.notes.trim(),
        });
        notifySuccess("Patrimônio e setor atualizados com sucesso!");
        showPatrimonioDialog.value = false;
      } catch (e) {
        notifyError(e?.response?.data?.error || "Erro ao salvar patrimônio.");
      } finally {
        savingPatrimonio.value = false;
      }
    }

    let summaryReqSeq = 0;

    async function getSummary() {
      const targetAgent = selectedAgent.value;
      if (!targetAgent) return;
      const reqId = ++summaryReqSeq;
      loading.value = true;
      try {
        const [agentData, fieldsData, tagData] = await Promise.all([
          fetchAgent(targetAgent),
          getCachedCustomFields().catch(() => customFieldsDefinitions.value),
          fetchAgentInventoryTag(targetAgent).catch(() => null),
        ]);
        if (reqId !== summaryReqSeq) return;
        summary.value = agentData;
        customFieldsDefinitions.value = fieldsData;
        inventoryTag.value = tagData;
        store.commit("setRefreshSummaryTab", false);
        if (agentData?.plat) {
          store.commit("setAgentPlatform", agentData.plat);
        }
      } catch (e) {
        console.error(e);
      } finally {
        if (reqId === summaryReqSeq) {
          loading.value = false;
        }
      }
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

    function copySpecValue(val) {
      if (!val) return;
      copyToClipboard(String(val)).then(() => {
        notifySuccess("Copiado para a área de transferência");
      });
    }

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
      displayMakeModel,
      displayCpuOrFunction,
      showGraphicsRow,
      isAgentlessAsset,
      store,
      rdpConnecting,
      showJoinAdDialog,
      joinAdLoading,
      joinAdForm,
      adDomainInfo,
      inventoryTag,
      showPatrimonioDialog,
      savingPatrimonio,
      patrimonioForm,

      // methods
      getSummary,
      refreshSummary,
      diskBarColor,
      runTakeControl,
      runRemoteBackground,
      openAgentWindow,
      connectNativeRDP,
      submitJoinAd,
      openPatrimonioDialog,
      submitPatrimonio,
      getEntityBadgeColor,
      copySpecValue,
    };
  },
};
</script>

<style scoped>
.trmm-summary-header {
  border-radius: 10px;
  min-height: 44px;
  gap: 8px 12px;
}

.trmm-summary-card {
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-summary-card--dark {
  background: rgba(20, 26, 36, 0.7);
}

.trmm-summary-card--light {
  background: #ffffff;
  border-color: rgba(15, 23, 42, 0.1);
}

.trmm-status-pill {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
}

.trmm-status-pill--positive {
  background: rgba(34, 197, 94, 0.16);
  color: #4ade80;
}

.trmm-status-pill--warning {
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
}

.trmm-status-pill--negative {
  background: rgba(239, 68, 68, 0.18);
  color: #f87171;
}

.trmm-status-dot-sm {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.trmm-sum-btn {
  border-radius: 7px !important;
  padding: 2px 10px !important;
  min-height: 28px !important;
  font-size: 12px !important;
  font-weight: 500;
  white-space: nowrap;
}

.trmm-sum-btn--primary {
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(25, 118, 210, 0.28);
}

.trmm-sum-btn--ghost {
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(148, 163, 184, 0.08);
}

.trmm-sum-btn--ghost:hover {
  background: rgba(148, 163, 184, 0.18);
  border-color: rgba(148, 163, 184, 0.42);
}

.trmm-card-title {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.015em;
}

.trmm-section-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.trmm-section-icon--blue {
  background: rgba(59, 130, 246, 0.18);
  color: #60a5fa;
}

.trmm-section-icon--emerald {
  background: rgba(16, 185, 129, 0.18);
  color: #34d399;
}

.trmm-section-icon--sky {
  background: rgba(14, 165, 233, 0.18);
  color: #38bdf8;
}

.trmm-section-icon--purple {
  background: rgba(168, 85, 247, 0.18);
  color: #c084fc;
}

.trmm-spec-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.trmm-spec-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 7px;
  border-radius: 7px;
  transition: background-color 0.14s ease;
}

.trmm-spec-row:hover {
  background: rgba(148, 163, 184, 0.08);
}

.trmm-spec-icon {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.trmm-spec-icon--blue {
  background: rgba(59, 130, 246, 0.14);
  color: #60a5fa;
}

.trmm-spec-icon--indigo {
  background: rgba(99, 102, 241, 0.16);
  color: #818cf8;
}

.trmm-spec-icon--teal {
  background: rgba(20, 184, 166, 0.16);
  color: #2dd4bf;
}

.trmm-spec-icon--slate {
  background: rgba(148, 163, 184, 0.14);
  color: #94a3b8;
}

.trmm-spec-icon--purple {
  background: rgba(168, 85, 247, 0.16);
  color: #c084fc;
}

.trmm-spec-icon--sky {
  background: rgba(14, 165, 233, 0.16);
  color: #38bdf8;
}

.trmm-spec-icon--emerald {
  background: rgba(34, 197, 94, 0.16);
  color: #4ade80;
}

.trmm-spec-icon--amber {
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
}

.trmm-spec-body {
  flex: 1 1 auto;
  min-width: 0;
}

.trmm-spec-label {
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #94a3b8;
  line-height: 1.2;
}

body.body--light .trmm-spec-label {
  color: #64748b;
}

.trmm-spec-value {
  font-size: 12.5px;
  font-weight: 500;
  line-height: 1.35;
  word-break: break-word;
}

.trmm-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.trmm-check-pill {
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12.5px;
}

.trmm-check-pill--positive {
  background: rgba(34, 197, 94, 0.14);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.trmm-check-pill--negative {
  background: rgba(239, 68, 68, 0.14);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.28);
}

.trmm-check-pill--warning {
  background: rgba(245, 158, 11, 0.14);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.28);
}

.trmm-check-pill--info {
  background: rgba(14, 165, 233, 0.14);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.28);
}

.trmm-empty-mini {
  border-radius: 8px;
  border: 1px dashed rgba(148, 163, 184, 0.24);
}

.trmm-empty-mini--dark {
  background: rgba(148, 163, 184, 0.04);
}

.trmm-empty-mini--light {
  background: #f8fafc;
}

.trmm-custom-field-row {
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.08);
}

.trmm-disk-card {
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.trmm-disk-card--dark {
  background: rgba(148, 163, 184, 0.06);
}

.trmm-disk-card--light {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.08);
}
</style>
