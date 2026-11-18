<template>
  <q-card style="width: 1340px; max-width: 98vw; max-height: 94vh" class="column no-wrap">
    <!-- Top Header -->
    <q-bar class="bg-teal-10 text-white">
      <q-icon name="inventory_2" class="q-mr-xs" />
      <div class="text-weight-bold">
        Central de Inventário Geral, Patrimônio e Ativos/Passivos de Rede
      </div>
      <q-space />
      <q-btn
        dense
        unelevated
        color="positive"
        icon="add_circle"
        label="Incluir Ativo / Passivo Manual"
        no-caps
        class="q-mr-xs q-px-sm"
        @click="openCreateManual"
      />
      <q-btn
        dense
        unelevated
        color="indigo-6"
        icon="upload_file"
        label="Importar CSV / Advanced IP Scanner"
        no-caps
        class="q-mr-xs q-px-sm"
        @click="openImportDialog"
      />
      <q-btn
        dense
        outline
        color="teal-2"
        icon="download"
        label="Exportar Excel (.CSV)"
        no-caps
        class="q-mr-xs"
        :disable="!filteredRows.length"
        @click="exportCsv"
      />
      <q-btn
        dense
        outline
        color="amber-3"
        icon="print"
        label="Imprimir / PDF"
        no-caps
        class="q-mr-xs"
        :disable="!filteredRows.length"
        @click="printReport"
      />
      <q-btn
        dense
        flat
        icon="refresh"
        :loading="loading"
        @click="loadInventory"
      >
        <q-tooltip>Atualizar Inventário</q-tooltip>
      </q-btn>
      <q-btn dense flat icon="close" v-close-popup @click="$emit('close')" />
    </q-bar>

    <!-- KPI Cards -->
    <q-card-section class="q-py-sm q-px-md bg-grey-10 text-white">
      <div class="row q-col-gutter-sm">
        <div class="col-6 col-sm-4 col-md-2">
          <q-card
            flat
            bordered
            class="bg-blue-grey-10 text-center q-pa-xs cursor-pointer"
            @click="resetQuickFilters"
          >
            <div class="text-caption text-grey-4">Total no Inventário</div>
            <div class="text-h5 text-weight-bold text-white">{{ summary.total }}</div>
          </q-card>
        </div>
        <div class="col-6 col-sm-4 col-md-2">
          <q-card
            flat
            bordered
            class="bg-blue-grey-10 text-center q-pa-xs cursor-pointer"
            @click="quickFilterAgent('agent_only')"
          >
            <div class="text-caption text-grey-4">Com Agente Tactical</div>
            <div class="text-h5 text-weight-bold text-light-blue-4">{{ summary.with_agent }}</div>
          </q-card>
        </div>
        <div class="col-6 col-sm-4 col-md-2">
          <q-card
            flat
            bordered
            class="bg-blue-grey-10 text-center q-pa-xs cursor-pointer"
            @click="quickFilterCategory('ativo_rede')"
          >
            <div class="text-caption text-grey-4">Ativos de Rede</div>
            <div class="text-h5 text-weight-bold text-teal-4">{{ summary.ativos_rede }}</div>
          </q-card>
        </div>
        <div class="col-6 col-sm-4 col-md-2">
          <q-card
            flat
            bordered
            class="bg-blue-grey-10 text-center q-pa-xs cursor-pointer"
            @click="quickFilterCategory('passivo_rede')"
          >
            <div class="text-caption text-grey-4">Passivos de Rede</div>
            <div class="text-h5 text-weight-bold text-amber-4">{{ summary.passivos_rede }}</div>
          </q-card>
        </div>
        <div class="col-6 col-sm-4 col-md-2">
          <q-card
            flat
            bordered
            class="bg-blue-grey-10 text-center q-pa-xs cursor-pointer"
            @click="quickFilterAgent('agentless_only')"
          >
            <div class="text-caption text-grey-4">Total Sem Agente</div>
            <div class="text-h5 text-weight-bold text-orange-4">{{ summary.agentless_total }}</div>
          </q-card>
        </div>
        <div class="col-6 col-sm-4 col-md-2">
          <q-card
            flat
            bordered
            class="bg-blue-grey-10 text-center q-pa-xs cursor-pointer"
            @click="quickFilterAgent('missing_patrimonio')"
          >
            <div class="text-caption text-grey-4">Com Nº Patrimônio</div>
            <div class="text-h5 text-weight-bold text-green-4">
              {{ summary.with_patrimonio }}
              <span class="text-caption text-grey-4">({{ summary.without_patrimonio }} p/ definir)</span>
            </div>
          </q-card>
        </div>
      </div>

      <!-- Company / Unit Distinction Strip -->
      <div v-if="companyUnitSummary.length" class="row items-center q-gutter-xs q-mt-xs">
        <span class="text-caption text-grey-4 text-weight-medium">Empresas / Unidades:</span>
        <q-chip
          clickable
          dense
          size="11px"
          :color="filterClient === 'Todos' && filterSite === 'Todos' ? 'primary' : 'grey-8'"
          text-color="white"
          @click="filterClient = 'Todos'; filterSite = 'Todos'"
        >
          Todas ({{ items.length }})
        </q-chip>
        <q-chip
          v-for="u in companyUnitSummary"
          :key="u.key"
          clickable
          dense
          size="11px"
          icon="business"
          :color="
            filterClient === u.client && filterSite === u.site
              ? getEntityBadgeColor(u.client)
              : 'blue-grey-9'
          "
          text-color="white"
          @click="selectCompanyUnit(u.client, u.site)"
        >
          <span class="text-weight-bold q-mr-xs">{{ u.client }}</span>
          <span class="text-grey-3">/ {{ u.site }} ({{ u.total }})</span>
          <q-tooltip>
            Empresa: {{ u.client }} &bull; Unidade: {{ u.site }} &bull; Com Agente: {{ u.withAgent }} &bull; Sem Agente: {{ u.agentless }}
          </q-tooltip>
        </q-chip>
      </div>

      <!-- Filter Row -->
      <div class="row q-col-gutter-sm items-center q-mt-xs">
        <div class="col-12 col-sm-3 col-md-2">
          <q-select
            v-model="filterClient"
            :options="clientFilterOptions"
            dense
            outlined
            dark
            label="Empresa / Cliente"
            @update:model-value="filterSite = 'Todos'"
          />
        </div>
        <div class="col-12 col-sm-3 col-md-2">
          <q-select
            v-model="filterSite"
            :options="siteFilterOptions"
            dense
            outlined
            dark
            label="Unidade / Filial"
          />
        </div>
        <div class="col-12 col-sm-3 col-md-3">
          <q-select
            v-model="filterCategory"
            :options="categoryFilterOptions"
            emit-value
            map-options
            dense
            outlined
            dark
            label="Classificação"
          />
        </div>
        <div class="col-12 col-sm-3 col-md-2">
          <q-select
            v-model="filterMode"
            :options="modeFilterOptions"
            emit-value
            map-options
            dense
            outlined
            dark
            label="Monitoramento / Tag"
          />
        </div>
        <div class="col-12 col-md-3">
          <q-input
            v-model="search"
            dense
            outlined
            dark
            clearable
            label="Buscar Patrimônio, Nome, IP, MAC, Setor..."
          >
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>
      </div>
    </q-card-section>

    <q-separator />

    <!-- Main Table -->
    <q-card-section class="col scroll q-pa-sm">
      <q-table
        :rows="filteredRows"
        :columns="columns"
        row-key="row_key"
        dense
        flat
        bordered
        :loading="loading"
        :pagination="{ rowsPerPage: 20, sortBy: 'name', descending: false }"
        no-data-label="Nenhum equipamento encontrado com os filtros selecionados."
      >
        <template v-slot:body-cell-patrimonio="props">
          <q-td :props="props">
            <q-chip
              v-if="props.row.patrimonio"
              dense
              clickable
              color="teal-8"
              text-color="white"
              icon="qr_code_2"
              @click="openEditRow(props.row)"
            >
              {{ props.row.patrimonio }}
              <q-tooltip>Clique para editar Patrimônio / Setor</q-tooltip>
            </q-chip>
            <q-btn
              v-else
              dense
              flat
              size="xs"
              color="amber-8"
              icon="edit"
              label="Definir Patrimônio"
              no-caps
              @click="openEditRow(props.row)"
            />
          </q-td>
        </template>

        <template v-slot:body-cell-name="props">
          <q-td :props="props">
            <div class="text-weight-bold">
              {{ props.row.name }}
              <q-badge
                v-if="!props.row.has_agent && props.row.matched_agent_id"
                color="positive"
                class="q-ml-xs"
              >
                Já possui Agente ({{ props.row.matched_agent_hostname }})
              </q-badge>
            </div>
            <div class="text-caption text-grey-5">
              {{ props.row.asset_subtype || "-" }}
              <span v-if="props.row.operating_system"> &bull; {{ props.row.operating_system }}</span>
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-category="props">
          <q-td :props="props">
            <q-badge :color="categoryBadgeColor(props.row.category)">
              {{ shortCategoryLabel(props.row.category) }}
            </q-badge>
          </q-td>
        </template>

        <template v-slot:body-cell-site="props">
          <q-td :props="props">
            <div class="row items-center q-gutter-x-xs">
              <q-badge
                :color="getEntityBadgeColor(props.row.client_name)"
                text-color="white"
                class="text-weight-bold"
              >
                {{ props.row.client_name }}
              </q-badge>
            </div>
            <div class="q-mt-xs">
              <q-badge
                outline
                :color="getEntityBadgeColor(props.row.site_name)"
                class="text-weight-medium"
              >
                {{ props.row.site_name }}
              </q-badge>
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-sector_location="props">
          <q-td :props="props">
            <div>{{ props.row.sector_location || "-" }}</div>
            <div class="text-caption text-grey-5" v-if="props.row.responsible || props.row.logged_in_username">
              Resp.: {{ props.row.responsible || props.row.logged_in_username }}
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-network="props">
          <q-td :props="props">
            <div>{{ props.row.ip_address || "-" }}</div>
            <div class="text-caption text-grey-5" v-if="props.row.mac_address">
              MAC: {{ props.row.mac_address }}
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-hardware="props">
          <q-td :props="props">
            <div>
              {{ [props.row.manufacturer, props.row.model_name].filter(Boolean).join(" ") || "-" }}
            </div>
            <div class="text-caption text-grey-5" v-if="props.row.serial_number">
              S/N: {{ props.row.serial_number }}
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-status_source="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.has_agent"
              :color="props.row.status === 'online' ? 'positive' : props.row.status === 'overdue' ? 'negative' : 'warning'"
              :text-color="props.row.status === 'offline' ? 'black' : 'white'"
            >
              Agente {{ props.row.status === "online" ? "Online" : props.row.status === "overdue" ? "Vencido" : "Offline" }}
            </q-badge>
            <q-badge v-else color="blue-grey-7">
              {{ sourceLabel(props.row.source) }}
            </q-badge>
            <div class="text-caption text-grey-5" v-if="!props.row.has_agent">
              Status: {{ props.row.status || "ativo" }}
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-actions="props">
          <q-td :props="props" class="text-right no-wrap">
            <q-btn
              dense
              flat
              size="sm"
              color="primary"
              icon="edit"
              @click="openEditRow(props.row)"
            >
              <q-tooltip>Editar Patrimônio / Dados</q-tooltip>
            </q-btn>
            <q-btn
              v-if="!props.row.has_agent && props.row.asset_id"
              dense
              flat
              size="sm"
              color="negative"
              icon="delete"
              @click="confirmDeleteRow(props.row)"
            >
              <q-tooltip>Remover ativo sem agente do inventário</q-tooltip>
            </q-btn>
          </q-td>
        </template>
      </q-table>
    </q-card-section>

    <!-- Sub-Dialog 1: Inclusão Manual / Edição de Patrimônio, Ativo & Passivo de Rede -->
    <q-dialog v-model="showFormDialog" persistent>
      <q-card style="width: 720px; max-width: 96vw">
        <q-bar class="bg-primary text-white">
          <q-icon :name="form.agent_id ? 'computer' : 'router'" class="q-mr-xs" />
          <div class="text-weight-bold">
            {{
              form.agent_id
                ? `Editar Patrimônio & Localização — ${form.name}`
                : form.asset_id
                  ? `Editar Item de Inventário — ${form.name}`
                  : "Inclusão Manual — Ativo / Passivo de Rede ou Equipamento sem Agente"
            }}
          </div>
          <q-space />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>

        <q-card-section class="q-gutter-y-sm">
          <q-banner v-if="form.agent_id" dense rounded class="bg-blue-grey-9 text-white">
            Este equipamento possui <b>Agente Tactical RMM</b> instalado (Nome/IP/Hardware vêm automaticamente do agente). Preencha o <b>Nº de Patrimônio</b>, Setor e Responsável para consolidar no inventário.
          </q-banner>

          <div class="row q-col-gutter-sm">
            <div class="col-12 col-sm-6">
              <q-select
                v-model="form.site_id"
                :options="siteSelectOptions"
                emit-value
                map-options
                dense
                outlined
                :disable="Boolean(form.agent_id)"
                label="Cliente / Unidade (Site) *"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.patrimonio"
                dense
                outlined
                autofocus
                label="Nº do Patrimônio / Plaqueta / Tombamento"
                placeholder="Ex: PAT-001452"
              >
                <template v-slot:prepend>
                  <q-icon name="qr_code_2" color="teal" />
                </template>
              </q-input>
            </div>
          </div>

          <div class="row q-col-gutter-sm" v-if="!form.agent_id">
            <div class="col-12 col-sm-6">
              <q-select
                v-model="form.category"
                :options="manualCategoryOptions"
                emit-value
                map-options
                dense
                outlined
                label="Classificação (Ativo / Passivo) *"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-select
                v-model="form.asset_subtype"
                :options="subtypePresetOptions"
                use-input
                new-value-mode="add-unique"
                input-debounce="0"
                dense
                outlined
                label="Tipo Específico (ex: Switch, Patch Panel, Rack...)"
              />
            </div>
          </div>

          <div class="row q-col-gutter-sm" v-else>
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.asset_subtype"
                dense
                outlined
                label="Tipo / Perfil (ex: Estação Recepção, Servidor AD...)"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.responsible"
                dense
                outlined
                label="Responsável / Usuário Principal"
              />
            </div>
          </div>

          <!-- Quick preset chips for Ativo / Passivo de Rede -->
          <div v-if="!form.agent_id" class="row items-center q-gutter-xs">
            <span class="text-caption text-grey-6">Atalhos rápidos:</span>
            <q-chip
              v-for="preset in quickPresets"
              :key="preset.label"
              clickable
              dense
              size="11px"
              color="blue-grey-8"
              text-color="white"
              @click="applyQuickPreset(preset)"
            >
              {{ preset.label }}
            </q-chip>
          </div>

          <div class="row q-col-gutter-sm" v-if="!form.agent_id">
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.name"
                dense
                outlined
                label="Nome / Identificação do Equipamento *"
                placeholder="Ex: SW-CORE-CERES-01 ou RACK-01-TI"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-select
                v-model="form.status"
                :options="statusSelectOptions"
                emit-value
                map-options
                dense
                outlined
                label="Status Operacional"
              />
            </div>
          </div>

          <div class="row q-col-gutter-sm" v-if="!form.agent_id">
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.ip_address"
                dense
                outlined
                label="Endereço IP (se aplicável)"
                placeholder="Ex: 192.168.10.254 (vazio p/ passivo)"
              />
            </div>
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.mac_address"
                dense
                outlined
                label="Endereço MAC (Opcional)"
                placeholder="Ex: AA:BB:CC:DD:EE:FF"
              />
            </div>
          </div>

          <div class="row q-col-gutter-sm" v-if="!form.agent_id">
            <div class="col-12 col-sm-4">
              <q-input v-model="form.manufacturer" dense outlined label="Fabricante" placeholder="Ex: Ubiquiti / Furukawa" />
            </div>
            <div class="col-12 col-sm-4">
              <q-input v-model="form.model_name" dense outlined label="Modelo" placeholder="Ex: USW-24-PoE / Cat6 24P" />
            </div>
            <div class="col-12 col-sm-4">
              <q-input v-model="form.serial_number" dense outlined label="Nº de Série" />
            </div>
          </div>

          <div class="row q-col-gutter-sm">
            <div class="col-12 col-sm-6">
              <q-input
                v-model="form.sector_location"
                dense
                outlined
                label="Setor / Sala / Rack / Porta"
                placeholder="Ex: Recepção Ceres / Rack 01 - U04"
              />
            </div>
            <div class="col-12 col-sm-6" v-if="!form.agent_id">
              <q-input
                v-model="form.responsible"
                dense
                outlined
                label="Responsável / Ponto Focal"
              />
            </div>
          </div>

          <q-input
            v-model="form.notes"
            type="textarea"
            rows="2"
            dense
            outlined
            label="Observações Técnicas / Portas / VLAN / Manutenção"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="positive"
            icon="save"
            label="Salvar no Inventário"
            :loading="savingForm"
            @click="submitForm"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Sub-Dialog 2: Importação CSV / Advanced IP Scanner -->
    <q-dialog v-model="showImportDialog" persistent>
      <q-card style="width: 1020px; max-width: 97vw; max-height: 92vh" class="column no-wrap">
        <q-bar class="bg-indigo-9 text-white">
          <q-icon name="upload_file" class="q-mr-xs" />
          <div class="text-weight-bold">
            Importar Tabela de Rede / Planilha (Advanced IP Scanner CSV, TSV ou Excel)
          </div>
          <q-space />
          <q-btn
            dense
            outline
            color="teal-2"
            icon="description"
            label="Baixar Modelo CSV"
            no-caps
            class="q-mr-sm"
            @click="downloadTemplateCsv"
          />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>

        <q-card-section class="q-gutter-y-sm col scroll">
          <q-banner dense rounded class="bg-indigo-10 text-white">
            Importa diretamente exportações do <b>Advanced IP Scanner</b> (<code>.csv</code> em Português ou Inglês) ou planilhas Excel (<code>Nome;IP;MAC;Fabricante;Patrimonio;Classificacao;Setor</code>) mesmo em equipamentos <b>sem agente instalado</b>.
          </q-banner>

          <div class="row q-col-gutter-sm items-center">
            <div class="col-12 col-sm-4">
              <q-select
                v-model="importSiteId"
                :options="siteSelectOptions"
                emit-value
                map-options
                dense
                outlined
                label="Unidade / Site de Destino *"
              />
            </div>
            <div class="col-12 col-sm-4">
              <q-select
                v-model="importDefaultCategory"
                :options="importCategoryOptions"
                emit-value
                map-options
                dense
                outlined
                label="Classificação Padrão dos Itens"
              />
            </div>
            <div class="col-12 col-sm-4">
              <q-file
                v-model="importFile"
                accept=".csv,.tsv,.txt"
                dense
                outlined
                clearable
                label="Selecionar arquivo .CSV / .TXT"
                @update:model-value="onImportFileSelected"
              >
                <template v-slot:prepend>
                  <q-icon name="attach_file" />
                </template>
              </q-file>
            </div>
          </div>

          <q-input
            v-model="importRawText"
            type="textarea"
            rows="4"
            dense
            outlined
            label="Ou cole aqui os dados da planilha / CSV do Advanced IP Scanner"
            placeholder="Status;Nome;IP;Fabricante;Endereço MAC;Patrimonio;Setor"
            @update:model-value="parseImportText"
          />

          <div class="row q-gutter-md items-center">
            <q-checkbox
              v-model="importReplacePrevious"
              dense
              label="Substituir importações CSV anteriores desta unidade (mantém inclusões manuais e agentes)"
            />
            <q-checkbox
              v-model="importSkipAgents"
              dense
              label="Ignorar IPs/Hostnames que já possuem Agente Tactical"
            />
            <q-space />
            <q-badge v-if="parsedImportRows.length" color="teal-7" class="q-pa-xs">
              {{ parsedImportRows.length }} linha(s) detectada(s) (Separador: {{ detectedDelimiterLabel }})
            </q-badge>
          </div>

          <!-- Preview Table -->
          <q-table
            v-if="parsedImportRows.length"
            :rows="parsedImportRows"
            :columns="importPreviewColumns"
            row-key="__idx"
            dense
            flat
            bordered
            :pagination="{ rowsPerPage: 8 }"
            style="max-height: 300px"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" v-close-popup />
          <q-btn
            color="primary"
            icon="cloud_upload"
            :label="`Importar ${parsedImportRows.length} Equipamento(s)`"
            :disable="!parsedImportRows.length || !importSiteId"
            :loading="importing"
            @click="submitImport"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useQuasar } from "quasar";
import {
  fetchInventoryAssets,
  saveInventoryAsset,
  deleteInventoryAsset,
  importInventoryAssets,
  getEntityBadgeColor,
  type InventoryAssetRow,
  type InventoryCategory,
  type InventoryImportRowInput,
  type InventorySiteOption,
  type InventorySummaryCounts,
} from "@/api/enhanced";
import { notifyError, notifySuccess } from "@/utils/notify";

const props = defineProps<{
  initialSiteId?: number | null;
}>();

defineEmits<{
  (e: "close"): void;
}>();

const $q = useQuasar();

const loading = ref(false);
const savingForm = ref(false);
const importing = ref(false);

const items = ref<InventoryAssetRow[]>([]);
const sites = ref<InventorySiteOption[]>([]);
const summary = ref<InventorySummaryCounts>({
  total: 0,
  with_agent: 0,
  agentless_total: 0,
  ativos_rede: 0,
  passivos_rede: 0,
  estacoes_sem_agente: 0,
  equipamentos_medicos: 0,
  impressoras_perifericos: 0,
  with_patrimonio: 0,
  without_patrimonio: 0,
  matched_with_agent: 0,
});

const filterClient = ref("Todos");
const filterSite = ref("Todos");
const filterCategory = ref("all");
const filterMode = ref<"all" | "agent_only" | "agentless_only" | "missing_patrimonio">("all");
const search = ref("");

const showFormDialog = ref(false);
const form = ref<{
  asset_id: number | null;
  agent_id: string | null;
  site_id: number | null;
  category: InventoryCategory;
  asset_subtype: string;
  patrimonio: string;
  name: string;
  ip_address: string;
  mac_address: string;
  manufacturer: string;
  model_name: string;
  serial_number: string;
  sector_location: string;
  responsible: string;
  status: string;
  notes: string;
}>({
  asset_id: null,
  agent_id: null,
  site_id: null,
  category: "ativo_rede",
  asset_subtype: "Switch Gerenciável",
  patrimonio: "",
  name: "",
  ip_address: "",
  mac_address: "",
  manufacturer: "",
  model_name: "",
  serial_number: "",
  sector_location: "",
  responsible: "",
  status: "ativo",
  notes: "",
});

const showImportDialog = ref(false);
const importSiteId = ref<number | null>(null);
const importDefaultCategory = ref("auto");
const importFile = ref<File | null>(null);
const importRawText = ref("");
const importReplacePrevious = ref(false);
const importSkipAgents = ref(false);
const detectedDelimiter = ref(";");
const parsedImportRows = ref<(InventoryImportRowInput & { __idx: number })[]>([]);

const categoryFilterOptions = [
  { label: "Todas as Classificações", value: "all" },
  { label: "Ativo Monitorado (Com Agente)", value: "ativo_monitorado" },
  { label: "Ativo de Rede (Switch/Roteador/AP/Firewall)", value: "ativo_rede" },
  { label: "Passivo de Rede (Rack/Patch Panel/Cabo/Tomada)", value: "passivo_rede" },
  { label: "Computador / Servidor (Sem Agente)", value: "estacao_sem_agente" },
  { label: "Equipamento Médico / Diagnose", value: "equipamento_medico" },
  { label: "Impressora / CFTV / Ponto / Periférico", value: "impressora_periferico" },
];

const manualCategoryOptions = categoryFilterOptions.filter((o) => o.value !== "all" && o.value !== "ativo_monitorado");

const importCategoryOptions = [
  { label: "Auto-detectar por Nome/Fabricante (Recomendado)", value: "auto" },
  ...manualCategoryOptions,
];

const modeFilterOptions = [
  { label: "Todos os Itens", value: "all" },
  { label: "Somente Sem Agente", value: "agentless_only" },
  { label: "Somente Com Agente", value: "agent_only" },
  { label: "Sem Nº de Patrimônio", value: "missing_patrimonio" },
];

const statusSelectOptions = [
  { label: "Ativo / Em Operação", value: "ativo" },
  { label: "Em Manutenção", value: "manutencao" },
  { label: "Reserva / Estoque", value: "reserva" },
  { label: "Inativo / Baixado", value: "inativo" },
];

const quickPresets = [
  { label: "Switch", category: "ativo_rede" as InventoryCategory, subtype: "Switch Gerenciável" },
  { label: "Roteador / Firewall", category: "ativo_rede" as InventoryCategory, subtype: "Roteador / Firewall" },
  { label: "Access Point Wi-Fi", category: "ativo_rede" as InventoryCategory, subtype: "Access Point (Wi-Fi)" },
  { label: "Rack de Rede", category: "passivo_rede" as InventoryCategory, subtype: "Rack de Rede" },
  { label: "Patch Panel", category: "passivo_rede" as InventoryCategory, subtype: "Patch Panel" },
  { label: "Cabeamento / Fibra / Ponto", category: "passivo_rede" as InventoryCategory, subtype: "Ponto de Rede / Cabeamento" },
  { label: "Nobreak", category: "passivo_rede" as InventoryCategory, subtype: "Nobreak / Estabilizador" },
  { label: "Impressora", category: "impressora_periferico" as InventoryCategory, subtype: "Impressora / Multifuncional" },
  { label: "Câmera IP / NVR", category: "impressora_periferico" as InventoryCategory, subtype: "Câmera IP / CFTV" },
  { label: "Equipamento Médico", category: "equipamento_medico" as InventoryCategory, subtype: "Equipamento Médico / Diagnose" },
];

const subtypePresetOptions = computed(() => {
  if (form.value.category === "passivo_rede") {
    return [
      "Rack de Rede",
      "Patch Panel",
      "Switch Não-Gerenciável",
      "Ponto de Rede / Keystone",
      "Cabeamento / Fibra Óptica",
      "Conversor de Mídia",
      "Nobreak / Estabilizador",
      "Régua / Organizador de Cabos",
    ];
  }
  if (form.value.category === "ativo_rede") {
    return [
      "Switch Gerenciável",
      "Switch PoE",
      "Roteador",
      "Firewall",
      "Access Point (Wi-Fi)",
      "Nobreak Gerenciável (SNMP)",
      "Controladora Wireless",
    ];
  }
  if (form.value.category === "equipamento_medico") {
    return [
      "Tomógrafo",
      "Ressonância Magnética",
      "Raio-X / CR / DR",
      "Ultrassom",
      "Mamógrafo",
      "Workstation DICOM",
      "Analisador Laboratorial",
    ];
  }
  if (form.value.category === "impressora_periferico") {
    return [
      "Impressora / Multifuncional",
      "Impressora Térmica / Etiqueta",
      "Scanner",
      "Câmera IP / NVR / DVR",
      "Relógio de Ponto",
      "Telefone IP / ATA",
    ];
  }
  return ["Desktop", "Notebook", "Servidor Físico / VM", "Thin Client / Mini PC", "Totem / Painel Senha"];
});

const columns = [
  { name: "patrimonio", label: "Nº Patrimônio", field: "patrimonio", sortable: true, align: "left" as const },
  { name: "name", label: "Equipamento / Hostname", field: "name", sortable: true, align: "left" as const },
  { name: "category", label: "Classificação", field: "category", sortable: true, align: "left" as const },
  { name: "site", label: "Empresa / Unidade", field: "client_name", sortable: true, align: "left" as const },
  { name: "sector_location", label: "Setor / Localização", field: "sector_location", sortable: true, align: "left" as const },
  { name: "network", label: "IP / MAC", field: "ip_address", sortable: true, align: "left" as const },
  { name: "hardware", label: "Fabricante / Modelo / Série", field: "manufacturer", sortable: true, align: "left" as const },
  { name: "status_source", label: "Origem / Status", field: "status", sortable: true, align: "center" as const },
  { name: "actions", label: "Ações", field: "actions", align: "right" as const },
];

const importPreviewColumns = [
  { name: "name", label: "Nome", field: "name", align: "left" as const },
  { name: "ip_address", label: "IP", field: "ip_address", align: "left" as const },
  { name: "mac_address", label: "MAC", field: "mac_address", align: "left" as const },
  { name: "manufacturer", label: "Fabricante", field: "manufacturer", align: "left" as const },
  { name: "patrimonio", label: "Patrimônio", field: "patrimonio", align: "left" as const },
  { name: "category", label: "Classificação", field: "category", align: "left" as const },
  { name: "sector_location", label: "Setor", field: "sector_location", align: "left" as const },
  { name: "notes", label: "Observações", field: "notes", align: "left" as const },
];

const siteSelectOptions = computed(() =>
  sites.value.map((s) => ({
    label: s.label,
    value: s.id,
  })),
);

const clientFilterOptions = computed(() => {
  const set = new Set<string>(sites.value.map((s) => s.client_name).filter(Boolean));
  return ["Todos", ...Array.from(set).sort()];
});

const siteFilterOptions = computed(() => {
  const filtered =
    filterClient.value === "Todos"
      ? sites.value
      : sites.value.filter((s) => s.client_name === filterClient.value);
  const set = new Set<string>(filtered.map((s) => s.name).filter(Boolean));
  return ["Todos", ...Array.from(set).sort()];
});

const companyUnitSummary = computed(() => {
  const map = new Map<
    string,
    { key: string; client: string; site: string; total: number; withAgent: number; agentless: number }
  >();
  for (const r of items.value) {
    const c = r.client_name || "Sem Empresa";
    const s = r.site_name || "Sem Unidade";
    const key = `${c}:::${s}`;
    const existing = map.get(key) || {
      key,
      client: c,
      site: s,
      total: 0,
      withAgent: 0,
      agentless: 0,
    };
    existing.total += 1;
    if (r.has_agent) existing.withAgent += 1;
    else existing.agentless += 1;
    map.set(key, existing);
  }
  return Array.from(map.values()).sort((a, b) => a.key.localeCompare(b.key));
});

function selectCompanyUnit(client: string, site: string) {
  if (filterClient.value === client && filterSite.value === site) {
    filterClient.value = "Todos";
    filterSite.value = "Todos";
  } else {
    filterClient.value = client;
    filterSite.value = site;
  }
}

const detectedDelimiterLabel = computed(() => {
  if (detectedDelimiter.value === ";") return "Ponto e vírgula (;)";
  if (detectedDelimiter.value === "\t") return "Tabulação (TAB)";
  return "Vírgula (,)";
});

const filteredRows = computed(() => {
  const q = search.value.trim().toLowerCase();
  return items.value.filter((r) => {
    if (filterClient.value !== "Todos" && r.client_name !== filterClient.value) return false;
    if (filterSite.value !== "Todos" && r.site_name !== filterSite.value) return false;
    if (filterCategory.value !== "all" && r.category !== filterCategory.value) return false;
    if (filterMode.value === "agent_only" && !r.has_agent) return false;
    if (filterMode.value === "agentless_only" && r.has_agent) return false;
    if (filterMode.value === "missing_patrimonio" && r.patrimonio.trim()) return false;
    if (q) {
      const hay = [
        r.patrimonio,
        r.name,
        r.ip_address,
        r.mac_address,
        r.manufacturer,
        r.model_name,
        r.serial_number,
        r.sector_location,
        r.responsible,
        r.asset_subtype,
        r.client_name,
        r.site_name,
        r.notes,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
});

function categoryBadgeColor(cat: string): string {
  switch (cat) {
    case "ativo_monitorado":
      return "light-blue-8";
    case "ativo_rede":
      return "teal-7";
    case "passivo_rede":
      return "amber-9";
    case "equipamento_medico":
      return "deep-purple-6";
    case "impressora_periferico":
      return "cyan-8";
    default:
      return "blue-grey-6";
  }
}

function shortCategoryLabel(cat: string): string {
  switch (cat) {
    case "ativo_monitorado":
      return "Agente Tactical";
    case "ativo_rede":
      return "Ativo de Rede";
    case "passivo_rede":
      return "Passivo de Rede";
    case "equipamento_medico":
      return "Equipamento Médico";
    case "impressora_periferico":
      return "Impressora / CFTV";
    default:
      return "PC / Servidor sem Agente";
  }
}

function sourceLabel(src: string): string {
  if (src === "advanced_ip_scanner") return "Advanced IP Scanner";
  if (src === "csv_import") return "Importação CSV";
  if (src === "lan_discovery") return "Descoberta LAN";
  if (src === "agent_sync") return "Agente Tactical";
  return "Inclusão Manual";
}

function resetQuickFilters() {
  filterCategory.value = "all";
  filterMode.value = "all";
}

function quickFilterCategory(cat: string) {
  filterCategory.value = filterCategory.value === cat ? "all" : cat;
  filterMode.value = "all";
}

function quickFilterAgent(mode: "agent_only" | "agentless_only" | "missing_patrimonio") {
  filterCategory.value = "all";
  filterMode.value = filterMode.value === mode ? "all" : mode;
}

function applyQuickPreset(preset: { label: string; category: InventoryCategory; subtype: string }) {
  form.value.category = preset.category;
  form.value.asset_subtype = preset.subtype;
}

function defaultSiteId(): number | null {
  if (props.initialSiteId && sites.value.some((s) => s.id === props.initialSiteId)) {
    return props.initialSiteId;
  }
  if (filterSite.value !== "Todos") {
    const found = sites.value.find(
      (s) => s.name === filterSite.value && (filterClient.value === "Todos" || s.client_name === filterClient.value),
    );
    if (found) return found.id;
  }
  return sites.value[0]?.id ?? null;
}

function openCreateManual() {
  form.value = {
    asset_id: null,
    agent_id: null,
    site_id: defaultSiteId(),
    category: "ativo_rede",
    asset_subtype: "Switch Gerenciável",
    patrimonio: "",
    name: "",
    ip_address: "",
    mac_address: "",
    manufacturer: "",
    model_name: "",
    serial_number: "",
    sector_location: "",
    responsible: "",
    status: "ativo",
    notes: "",
  };
  showFormDialog.value = true;
}

function openEditRow(row: InventoryAssetRow) {
  form.value = {
    asset_id: row.asset_id,
    agent_id: row.agent_id,
    site_id: row.site_id,
    category: row.category,
    asset_subtype: row.asset_subtype || "",
    patrimonio: row.patrimonio || "",
    name: row.name,
    ip_address: row.ip_address || "",
    mac_address: row.mac_address || "",
    manufacturer: row.manufacturer || "",
    model_name: row.model_name || "",
    serial_number: row.serial_number || "",
    sector_location: row.sector_location || "",
    responsible: row.responsible || "",
    status: row.status || "ativo",
    notes: row.notes || "",
  };
  showFormDialog.value = true;
}

function extractErrMsg(e: unknown, fallback: string): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { error?: unknown } } }).response;
    if (resp?.data?.error) return String(resp.data.error);
  }
  return fallback;
}

async function submitForm() {
  if (!form.value.agent_id) {
    if (!form.value.site_id) {
      notifyError("Selecione a Unidade / Site.");
      return;
    }
    if (!form.value.name.trim()) {
      notifyError("Informe o Nome / Identificação do equipamento.");
      return;
    }
  }

  savingForm.value = true;
  try {
    await saveInventoryAsset({
      asset_id: form.value.asset_id,
      agent_id: form.value.agent_id,
      site_id: form.value.site_id ?? undefined,
      category: form.value.category,
      asset_subtype: form.value.asset_subtype,
      patrimonio: form.value.patrimonio,
      name: form.value.name,
      ip_address: form.value.ip_address,
      mac_address: form.value.mac_address,
      manufacturer: form.value.manufacturer,
      model_name: form.value.model_name,
      serial_number: form.value.serial_number,
      sector_location: form.value.sector_location,
      responsible: form.value.responsible,
      status: form.value.status,
      notes: form.value.notes,
    });
    notifySuccess("Registro salvo no inventário com sucesso!");
    showFormDialog.value = false;
    await loadInventory();
  } catch (e: unknown) {
    notifyError(extractErrMsg(e, "Erro ao salvar item no inventário."));
  } finally {
    savingForm.value = false;
  }
}

function confirmDeleteRow(row: InventoryAssetRow) {
  if (!row.asset_id) return;
  $q.dialog({
    title: "Remover ativo sem agente",
    message: `Deseja remover "${row.name}"${row.patrimonio ? ` (Patrimônio: ${row.patrimonio})` : ""} do inventário?`,
    cancel: true,
    ok: { label: "Remover", color: "negative" },
  }).onOk(async () => {
    try {
      await deleteInventoryAsset(row.asset_id!);
      notifySuccess("Item removido do inventário.");
      await loadInventory();
    } catch (e: unknown) {
      notifyError(extractErrMsg(e, "Erro ao remover item."));
    }
  });
}

function openImportDialog() {
  importSiteId.value = defaultSiteId();
  importFile.value = null;
  importRawText.value = "";
  parsedImportRows.value = [];
  showImportDialog.value = true;
}

async function onImportFileSelected(file: File | null) {
  if (!file) return;
  try {
    const buffer = await file.arrayBuffer();
    let text = new TextDecoder("utf-8").decode(buffer);
    if (text.includes("\uFFFD")) {
      text = new TextDecoder("windows-1252").decode(buffer);
    }
    importRawText.value = text.replace(/^\uFEFF/, "");
    parseImportText(importRawText.value);
  } catch {
    notifyError("Falha ao ler arquivo selecionado.");
  }
}

function normalizeHeader(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function detectDelimiter(sampleLine: string): string {
  const counts = [
    { d: ";", n: (sampleLine.match(/;/g) || []).length },
    { d: "\t", n: (sampleLine.match(/\t/g) || []).length },
    { d: ",", n: (sampleLine.match(/,/g) || []).length },
  ];
  counts.sort((a, b) => b.n - a.n);
  return counts[0].n > 0 ? counts[0].d : ";";
}

function splitCsvLine(line: string, delim: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === delim && !inQuotes) {
      out.push(cur.trim());
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur.trim());
  return out;
}

function mapCsvFieldKey(headerNorm: string): keyof InventoryImportRowInput | null {
  const aliases: { keys: string[]; field: keyof InventoryImportRowInput }[] = [
    { keys: ["patrimonio", "n patrimonio", "no patrimonio", "numero patrimonio", "plaqueta", "tombamento", "asset tag", "asset_tag", "tag"], field: "patrimonio" },
    { keys: ["nome", "name", "hostname", "host", "computador", "equipamento", "dispositivo", "device", "netbios"], field: "name" },
    { keys: ["ip", "ip address", "endereco ip", "ipv4", "ip_address"], field: "ip_address" },
    { keys: ["mac", "mac address", "endereco mac", "mac_address"], field: "mac_address" },
    { keys: ["fabricante", "manufacturer", "vendor", "marca"], field: "manufacturer" },
    { keys: ["modelo", "model", "model_name"], field: "model_name" },
    { keys: ["serial", "serial number", "n de serie", "numero de serie", "service tag", "sn"], field: "serial_number" },
    { keys: ["categoria", "classificacao", "category", "ativo passivo", "ativo_passivo"], field: "category" },
    { keys: ["tipo", "subtipo", "type", "asset_subtype"], field: "asset_subtype" },
    { keys: ["setor", "local", "localizacao", "sector", "location", "sala", "departamento", "rack"], field: "sector_location" },
    { keys: ["responsavel", "responsible", "usuario", "user"], field: "responsible" },
    { keys: ["os", "so", "sistema", "sistema operacional", "operating system"], field: "operating_system" },
    { keys: ["status", "estado", "situacao"], field: "status" },
    { keys: ["comments", "comentarios", "comentario", "observacoes", "observacao", "notes", "obs", "description", "descricao"], field: "notes" },
  ];
  for (const group of aliases) {
    if (group.keys.includes(headerNorm)) return group.field;
  }
  return null;
}

function parseImportText(text: string | number | null) {
  const cleanText = String(text || "").replace(/^\uFEFF/, "").trim();
  if (!cleanText) {
    parsedImportRows.value = [];
    return;
  }
  const lines = cleanText.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (!lines.length) {
    parsedImportRows.value = [];
    return;
  }

  const delim = detectDelimiter(lines[0]);
  detectedDelimiter.value = delim;

  const firstCells = splitCsvLine(lines[0], delim);
  const mappedHeaders = firstCells.map((h) => mapCsvFieldKey(normalizeHeader(h)));
  const hasHeaderRow = mappedHeaders.some(Boolean);

  const dataLines = hasHeaderRow ? lines.slice(1) : lines;
  const rows: (InventoryImportRowInput & { __idx: number })[] = [];

  dataLines.forEach((line, idx) => {
    const cols = splitCsvLine(line, delim);
    const row: InventoryImportRowInput & { __idx: number } = {
      __idx: idx + 1,
      name: "",
    };

    if (hasHeaderRow) {
      cols.forEach((val, colIdx) => {
        const key = mappedHeaders[colIdx];
        if (!key || !val) return;
        row[key] = val;
      });
    } else {
      // Positional fallback matching typical Advanced IP Scanner layout: Status;Name;IP;Manufacturer;MAC
      row.status = cols[0] || "ativo";
      row.name = cols[1] || cols[2] || "";
      row.ip_address = cols[2] || "";
      row.manufacturer = cols[3] || "";
      row.mac_address = cols[4] || "";
    }

    if (row.status) {
      const st = row.status.toLowerCase();
      if (st === "alive" || st === "vivo" || st === "on") row.status = "ativo";
      else if (st === "dead" || st === "morto" || st === "off") row.status = "offline";
      else if (st === "unknown" || st === "desconhecido") row.status = "desconhecido";
    }

    if (!row.name && row.ip_address) {
      row.name = row.ip_address;
    }
    if (row.name || row.ip_address || row.patrimonio) {
      rows.push(row);
    }
  });

  parsedImportRows.value = rows;
}

async function submitImport() {
  if (!importSiteId.value || !parsedImportRows.value.length) return;
  importing.value = true;
  try {
    const cleanRows: InventoryImportRowInput[] = parsedImportRows.value.map((r) => ({
      name: r.name,
      ip_address: r.ip_address,
      mac_address: r.mac_address,
      patrimonio: r.patrimonio,
      manufacturer: r.manufacturer,
      model_name: r.model_name,
      serial_number: r.serial_number,
      operating_system: r.operating_system,
      sector_location: r.sector_location,
      responsible: r.responsible,
      status: r.status,
      notes: r.notes,
      category: r.category,
      asset_subtype: r.asset_subtype,
    }));
    const res = await importInventoryAssets({
      site_id: importSiteId.value,
      default_category: importDefaultCategory.value,
      default_source: "advanced_ip_scanner",
      replace_site_imports: importReplacePrevious.value,
      skip_matched_agents: importSkipAgents.value,
      rows: cleanRows,
    });
    notifySuccess(
      `Importação em ${res.site_name}: ${res.created} criado(s), ${res.updated} atualizado(s)` +
        (res.skipped_agents ? `, ${res.skipped_agents} já monitorado(s) ignorado(s)` : "") +
        ".",
    );
    showImportDialog.value = false;
    await loadInventory();
  } catch (e: unknown) {
    notifyError(extractErrMsg(e, "Erro ao importar tabela para o inventário."));
  } finally {
    importing.value = false;
  }
}

function downloadTemplateCsv() {
  const csv = [
    "Patrimonio;Classificacao;Subtipo;Nome;IP;MAC;Fabricante;Modelo;Serie;Setor;Responsavel;Status;Observacoes",
    "PAT-00101;ativo_rede;Switch Gerenciável;SW-CORE-CERES-01;192.168.10.2;AA:BB:CC:DD:EE:01;Ubiquiti;USW-24-PoE;SN123456;Sala TI - Rack 01;TI CRD;ativo;Switch principal 24 portas PoE",
    "PAT-00102;passivo_rede;Patch Panel;PP-01-CAT6-CERES;;;Furukawa;Cat6 24 Portas;SN987654;Sala TI - Rack 01 - U02;TI CRD;ativo;24 pontos identificados",
    "PAT-00103;equipamento_medico;Ultrassom;US-SALA02-CERES;192.168.10.45;AA:BB:CC:DD:EE:02;GE Healthcare;Voluson;;Sala Exame 02;Coord. Imagem;ativo;Sem agente - DICOM",
  ].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "modelo-inventario-ativos-passivos.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function exportCsv() {
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const headers = [
    "Patrimonio",
    "Equipamento",
    "Classificacao",
    "Subtipo",
    "Cliente",
    "Unidade/Site",
    "Setor/Localizacao",
    "Responsavel",
    "IP Local",
    "MAC",
    "Fabricante",
    "Modelo",
    "N Serie",
    "Sistema Operacional",
    "Possui Agente",
    "Status",
    "Origem",
    "Observacoes",
  ];
  const lines = [headers.map(esc).join(";")];
  for (const r of filteredRows.value) {
    lines.push(
      [
        r.patrimonio,
        r.name,
        shortCategoryLabel(r.category),
        r.asset_subtype,
        r.client_name,
        r.site_name,
        r.sector_location,
        r.responsible || r.logged_in_username,
        r.ip_address,
        r.mac_address,
        r.manufacturer,
        r.model_name,
        r.serial_number,
        r.operating_system,
        r.has_agent ? "Sim" : r.matched_agent_id ? `Nao (Agente: ${r.matched_agent_hostname})` : "Nao",
        r.status,
        sourceLabel(r.source),
        r.notes,
      ]
        .map(esc)
        .join(";"),
    );
  }
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `inventario-patrimonio-tactical-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function printReport() {
  const w = window.open("", "_blank");
  if (!w) {
    notifyError("Desbloqueie pop-ups para gerar a versão de impressão/PDF.");
    return;
  }
  const escHtml = (s: unknown) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  const rowsHtml = filteredRows.value
    .map(
      (r) => `<tr>
        <td>${escHtml(r.patrimonio || "-")}</td>
        <td><b>${escHtml(r.name)}</b><br><small>${escHtml(r.asset_subtype)}</small></td>
        <td>${escHtml(shortCategoryLabel(r.category))}</td>
        <td>${escHtml(r.client_name)} / ${escHtml(r.site_name)}</td>
        <td>${escHtml(r.sector_location || "-")}</td>
        <td>${escHtml(r.ip_address || "-")}<br><small>${escHtml(r.mac_address || "")}</small></td>
        <td>${escHtml([r.manufacturer, r.model_name].filter(Boolean).join(" ") || "-")}</td>
        <td>${escHtml(r.has_agent ? "Com Agente" : "Sem Agente")}</td>
      </tr>`,
    )
    .join("");
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Relatório de Inventário & Patrimônio - Tactical RMM</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 20px; color: #111; }
      h2 { margin: 0 0 6px 0; }
      .meta { font-size: 12px; color: #555; margin-bottom: 14px; }
      table { width: 100%; border-collapse: collapse; font-size: 11px; }
      th, td { border: 1px solid #ccc; padding: 5px 6px; text-align: left; vertical-align: top; }
      th { background: #0f4c5c; color: #fff; }
      tr:nth-child(even) { background: #f8f9fa; }
      @media print { body { margin: 8mm; } }
    </style></head><body>
    <h2>Relatório Consolidado de Inventário, Patrimônio e Rede</h2>
    <div class="meta">Gerado em ${escHtml(new Date().toLocaleString("pt-BR"))} &bull; Total listado: ${filteredRows.value.length} ativo(s) &bull; Filtro Unidade: ${escHtml(filterSite.value)}</div>
    <table><thead><tr>
      <th>Patrimônio</th><th>Equipamento</th><th>Classificação</th><th>Unidade</th><th>Setor / Local</th><th>IP / MAC</th><th>Fabricante / Modelo</th><th>Monitoramento</th>
    </tr></thead><tbody>${rowsHtml}</tbody></table>
    <script>window.onload = () => window.print();<\/script>
  </body></html>`);
  w.document.close();
}

async function loadInventory() {
  loading.value = true;
  try {
    const res = await fetchInventoryAssets();
    items.value = res.items || [];
    sites.value = res.sites || [];
    summary.value = res.summary || summary.value;
    if (props.initialSiteId) {
      const targetSite = sites.value.find((s) => s.id === props.initialSiteId);
      if (targetSite) {
        filterClient.value = targetSite.client_name;
        filterSite.value = targetSite.name;
      }
    }
  } catch (e: unknown) {
    notifyError(extractErrMsg(e, "Erro ao carregar inventário geral."));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadInventory();
});
</script>
