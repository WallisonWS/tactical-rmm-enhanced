<template>
  <div class="trmm-wmi-wrapper">
    <div
      v-if="parsedCards.length === 0"
      class="trmm-wmi-empty column items-center justify-center q-pa-lg text-center"
      :class="$q.dark.isActive ? 'trmm-wmi-empty--dark' : 'trmm-wmi-empty--light'"
    >
      <q-icon name="inventory_2" size="34px" color="grey-6" class="q-mb-xs" />
      <div class="text-subtitle2 text-weight-medium">
        {{
          search && search.trim()
            ? "Nenhuma propriedade encontrada para o filtro informado"
            : "Sem dados WMI disponíveis para esta categoria"
        }}
      </div>
      <div class="text-caption text-grey-6 q-mt-xs">
        {{
          search && search.trim()
            ? "Tente limpar a busca ou desativar 'Ocultar vazios'."
            : "Dispositivos de inventário LAN sem agente não reportam telemetria WMI."
        }}
      </div>
    </div>

    <div v-else class="q-gutter-y-md q-pb-md">
      <div
        v-for="(card, cardIdx) in parsedCards"
        :key="cardIdx"
        class="trmm-wmi-card"
        :class="$q.dark.isActive ? 'trmm-wmi-card--dark' : 'trmm-wmi-card--light'"
      >
        <div class="trmm-wmi-card-header row items-center justify-between q-px-md q-py-xs">
          <div class="row items-center no-wrap" style="gap: 8px; min-width: 0">
            <div class="trmm-wmi-index-pill">
              #{{ cardIdx + 1 }}
            </div>
            <span class="text-subtitle2 text-weight-bold ellipsis">
              {{ card.title }}
            </span>
          </div>
          <q-badge
            rounded
            :color="$q.dark.isActive ? 'blue-grey-9' : 'blue-grey-1'"
            :text-color="$q.dark.isActive ? 'grey-4' : 'blue-grey-8'"
            class="text-weight-medium"
            style="font-size: 11px; padding: 2px 8px"
          >
            {{ card.entries.length }} {{ card.entries.length === 1 ? "campo" : "campos" }}
          </q-badge>
        </div>

        <div class="trmm-wmi-grid q-pa-sm">
          <div
            v-for="entry in card.entries"
            :key="entry.key"
            class="trmm-wmi-cell row items-center justify-between no-wrap"
            :class="$q.dark.isActive ? 'trmm-wmi-cell--dark' : 'trmm-wmi-cell--light'"
          >
            <div class="col" style="min-width: 0">
              <div class="trmm-wmi-key ellipsis" :title="entry.key">
                {{ entry.key }}
              </div>
              <div class="q-mt-xs">
                <span
                  v-if="entry.kind === 'bool-true'"
                  class="trmm-wmi-bool trmm-wmi-bool--true"
                >
                  <q-icon name="check_circle" size="13px" class="q-mr-xs" />
                  Sim (true)
                </span>
                <span
                  v-else-if="entry.kind === 'bool-false'"
                  class="trmm-wmi-bool trmm-wmi-bool--false"
                >
                  <q-icon name="cancel" size="13px" class="q-mr-xs" />
                  Não (false)
                </span>
                <span v-else-if="entry.kind === 'empty'" class="text-caption text-grey-6">
                  —
                </span>
                <span
                  v-else
                  class="trmm-wmi-val"
                  :title="entry.displayValue"
                >
                  {{ entry.displayValue }}
                </span>
              </div>
            </div>

            <q-btn
              v-if="entry.kind !== 'empty'"
              dense
              flat
              round
              size="xs"
              icon="content_copy"
              color="grey-5"
              class="trmm-wmi-copy q-ml-xs"
              @click="copyValueToClip(entry.rawString)"
            >
              <q-tooltip>Copiar valor</q-tooltip>
            </q-btn>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from "vue";
import { copyToClipboard } from "quasar";
import { notifySuccess } from "@/utils/notify";

const TITLE_KEYS = [
  "Caption",
  "Name",
  "Description",
  "Model",
  "Product",
  "DeviceID",
  "AdapterName",
];

function isEmptyVal(val) {
  if (val === null || val === undefined) return true;
  if (typeof val === "string") return val.trim() === "";
  if (Array.isArray(val)) return val.length === 0;
  return false;
}

function classifyValue(val) {
  if (val === true || val === "true") {
    return { kind: "bool-true", displayValue: "true", rawString: "true" };
  }
  if (val === false || val === "false") {
    return { kind: "bool-false", displayValue: "false", rawString: "false" };
  }
  if (isEmptyVal(val)) {
    return { kind: "empty", displayValue: "—", rawString: "" };
  }
  const str = Array.isArray(val) ? val.join(", ") : String(val);
  return { kind: "text", displayValue: str, rawString: str };
}

export default {
  name: "WmiDetail",
  props: {
    info: {
      type: [Array, Object],
      default: () => [],
    },
    search: {
      type: String,
      default: "",
    },
    hideEmpty: {
      type: Boolean,
      default: true,
    },
    categoryLabel: {
      type: String,
      default: "",
    },
  },
  setup(props) {
    const parsedCards = computed(() => {
      if (!props.info) return [];
      const items = Array.isArray(props.info) ? props.info : [props.info];
      const q = (props.search || "").trim().toLowerCase();
      const result = [];

      items.forEach((group, idx) => {
        if (!group) return;
        const rows = Array.isArray(group) ? group : [group];
        const flatEntries = [];
        let smartTitle = "";

        rows.forEach((obj) => {
          if (!obj || typeof obj !== "object") return;
          Object.entries(obj).forEach(([k, v]) => {
            if (!smartTitle && TITLE_KEYS.includes(k) && !isEmptyVal(v)) {
              smartTitle = Array.isArray(v) ? v.join(", ") : String(v);
            }
            const classified = classifyValue(v);
            if (props.hideEmpty && classified.kind === "empty") return;
            if (
              q &&
              !k.toLowerCase().includes(q) &&
              !classified.rawString.toLowerCase().includes(q)
            ) {
              return;
            }
            flatEntries.push({
              key: k,
              ...classified,
            });
          });
        });

        if (flatEntries.length > 0) {
          result.push({
            title:
              smartTitle ||
              (props.categoryLabel
                ? `${props.categoryLabel} #${idx + 1}`
                : `Item #${idx + 1}`),
            entries: flatEntries,
          });
        }
      });

      return result;
    });

    function copyValueToClip(val) {
      copyToClipboard(String(val)).then(() => {
        notifySuccess("Copiado para a área de transferência");
      });
    }

    return {
      parsedCards,
      copyValueToClip,
    };
  },
};
</script>

<style scoped>
.trmm-wmi-wrapper {
  width: 100%;
}

.trmm-wmi-empty {
  border-radius: 10px;
  border: 1px dashed rgba(148, 163, 184, 0.28);
}

.trmm-wmi-empty--dark {
  background: rgba(15, 23, 42, 0.28);
}

.trmm-wmi-empty--light {
  background: rgba(241, 245, 249, 0.7);
}

.trmm-wmi-card {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-wmi-card--dark {
  background: rgba(20, 26, 36, 0.72);
}

.trmm-wmi-card--light {
  background: #ffffff;
  border-color: rgba(15, 23, 42, 0.1);
}

.trmm-wmi-card-header {
  min-height: 36px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(148, 163, 184, 0.06);
}

.trmm-wmi-index-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 6px;
  background: rgba(25, 118, 210, 0.2);
  color: #60a5fa;
  flex-shrink: 0;
}

body.body--light .trmm-wmi-index-pill {
  color: #1d4ed8;
  background: rgba(25, 118, 210, 0.12);
}

.trmm-wmi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
}

.trmm-wmi-cell {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid transparent;
  transition: background-color 0.14s ease, border-color 0.14s ease;
}

.trmm-wmi-cell--dark {
  background: rgba(148, 163, 184, 0.055);
  border-color: rgba(148, 163, 184, 0.09);
}

.trmm-wmi-cell--dark:hover {
  background: rgba(148, 163, 184, 0.11);
  border-color: rgba(96, 165, 250, 0.35);
}

.trmm-wmi-cell--light {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.07);
}

.trmm-wmi-cell--light:hover {
  background: #eff6ff;
  border-color: rgba(25, 118, 210, 0.28);
}

.trmm-wmi-key {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.045em;
  color: #94a3b8;
}

body.body--light .trmm-wmi-key {
  color: #64748b;
}

.trmm-wmi-val {
  display: inline-block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  font-weight: 500;
  word-break: break-word;
  line-height: 1.35;
}

.trmm-wmi-bool {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
}

.trmm-wmi-bool--true {
  background: rgba(34, 197, 94, 0.16);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.32);
}

body.body--light .trmm-wmi-bool--true {
  color: #15803d;
  background: rgba(34, 197, 94, 0.12);
}

.trmm-wmi-bool--false {
  background: rgba(148, 163, 184, 0.14);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.25);
}

body.body--light .trmm-wmi-bool--false {
  color: #475569;
}

.trmm-wmi-copy {
  opacity: 0.45;
  transition: opacity 0.14s ease, color 0.14s ease;
  flex-shrink: 0;
}

.trmm-wmi-cell:hover .trmm-wmi-copy {
  opacity: 1;
}
</style>
