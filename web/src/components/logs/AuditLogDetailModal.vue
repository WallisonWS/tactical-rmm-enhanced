<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card class="q-dialog-plugin" style="min-width: 72vw; max-width: 92vw" data-no-translate="true">
      <q-bar class="bg-primary text-white">
        <q-icon name="travel_explore" size="sm" class="q-mr-xs" />
        <div class="text-weight-bold ellipsis">
          Detalhes do Evento de Auditoria — {{ log?.message || "Registro" }}
        </div>
        <q-space />
        <q-btn dense flat icon="close" v-close-popup />
      </q-bar>

      <q-card-section class="q-pb-xs">
        <div class="row q-col-gutter-sm text-caption">
          <div class="col-12 col-sm-3">
            <b>Usuário:</b> {{ log?.username || "-" }}
          </div>
          <div class="col-12 col-sm-3">
            <b>Computador:</b> {{ log?.agent || "-" }}
          </div>
          <div class="col-12 col-sm-3">
            <b>Ação:</b> {{ log?.action || "-" }} ({{ log?.object_type || "-" }})
          </div>
          <div class="col-12 col-sm-3">
            <b>IP de Origem:</b> {{ log?.ip_address || log?.debug_info?.ip || "-" }}
          </div>
        </div>
      </q-card-section>

      <q-separator />

      <q-card-section class="scroll trmm-scroll-pane" style="max-height: 62vh">
        <q-splitter v-model="splitterModel">
          <template v-slot:before>
            <div class="q-pr-sm">
              <div class="text-subtitle2 text-weight-bold q-mb-xs">Estado Anterior (Before)</div>
              <pre style="white-space: pre-wrap; word-break: break-word; font-size: 12px">{{ JSON.stringify(log?.before_value ?? null, null, 2) }}</pre>
            </div>
          </template>

          <template v-slot:after>
            <div class="q-pl-sm">
              <div class="text-subtitle2 text-weight-bold q-mb-xs">Valor Novo / Saída (After)</div>
              <pre style="white-space: pre-wrap; word-break: break-word; font-size: 12px">{{ JSON.stringify(log?.after_value ?? null, null, 2) }}</pre>
            </div>
          </template>
        </q-splitter>
      </q-card-section>

      <q-separator />

      <q-card-actions align="right">
        <q-btn flat dense no-caps color="primary" label="Fechar" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script>
import { useDialogPluginComponent } from "quasar";

export default {
  name: "AuditLogDetail",
  emits: [...useDialogPluginComponent.emits],
  props: {
    log: {
      type: Object,
      required: true,
    },
  },
  setup() {
    const { dialogRef, onDialogHide } = useDialogPluginComponent();

    return {
      splitterModel: 50,
      dialogRef,
      onDialogHide,
    };
  },
};
</script>
