<template>
  <q-card-section class="q-px-xs q-pb-md q-pt-xs" v-if="hasText">
    <script-output-copy-clip label="Live Output" :data="outputText" />
    <q-separator class="q-my-sm" />
  </q-card-section>
  <div class="command-stream" ref="streamContainer" v-if="hasText">
    <div class="terminal">
      <pre class="mt-0">{{ outputText }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  onMounted,
  onUnmounted,
  watchEffect,
  watch,
  nextTick,
  computed,
} from "vue";
import { useTemplateRef } from "vue";
import { useAgentCmdWSConnection } from "@/websocket/agent";
import ScriptOutputCopyClip from "@/components/scripts/ScriptOutputCopyClip.vue";
import { uid } from "quasar";

const props = defineProps({
  agentId: { type: String, required: true },
  cmd: { type: String, required: true },
  shell: { type: String, required: true },
  run_as_user: { type: Boolean, required: true },
  custom_shell: { type: String, required: false },
  timeout: { type: Number, default: 10 },
});

// emits
const emit = defineEmits(["updateOutput", "streamLoaded", "streamClosed"]);

const cmdId = uid();
const { send, data, reset, close, status } = useAgentCmdWSConnection(
  props.agentId,
  cmdId,
);

const outputText = ref("");
const streamContainer = useTemplateRef<HTMLElement>("streamContainer");
let firstChunk = false;
let sentCommand = false;
let noOutputTimer: ReturnType<typeof setTimeout> | null = null;

const hasText = computed(() => outputText.value.trim() !== "");

function clearNoOutputTimer() {
  if (noOutputTimer) {
    clearTimeout(noOutputTimer);
    noOutputTimer = null;
  }
}

watchEffect(() => {
  if (data.value.length) {
    clearNoOutputTimer();
    const textChunks = data.value
      .map((msg) => msg.output)
      .filter((o): o is string => typeof o === "string" && o.length > 0);
    if (textChunks.length) {
      outputText.value = textChunks.join("\n");
      emit("updateOutput", outputText.value);
    }

    if (!firstChunk && textChunks.length > 0) {
      firstChunk = true;
      emit("streamLoaded");
    }

    if (data.value.some((msg) => msg.done === true)) {
      emit("streamClosed");
    }

    nextTick(() => {
      if (streamContainer.value) {
        streamContainer.value.scrollTop = streamContainer.value.scrollHeight;
      }
    });
  }
});

watch(
  status,
  (st) => {
    if (st === "OPEN" && !sentCommand) {
      sentCommand = true;
      send(
        JSON.stringify({
          shell: props.shell,
          cmd: props.cmd,
          timeout: props.timeout,
          run_as_user: props.run_as_user,
          custom_shell: props.custom_shell,
          stream: true,
          cmd_id: cmdId,
        }),
      );
      clearNoOutputTimer();
      noOutputTimer = setTimeout(
        () => {
          if (!firstChunk) {
            outputText.value = "[ERRO] O agente não respondeu via NATS no tempo limite.";
            emit("updateOutput", outputText.value);
            emit("streamClosed");
          }
        },
        (Math.max(10, props.timeout) + 5) * 1000,
      );
    } else if (st === "CLOSED") {
      clearNoOutputTimer();
      if (!firstChunk) {
        outputText.value = "[ERRO] Conexão WebSocket encerrada antes de receber resposta do agente.";
        emit("updateOutput", outputText.value);
      }
      emit("streamClosed");
    }
  },
  { immediate: true },
);

onMounted(() => {
  outputText.value = "";
  reset();
});

onUnmounted(() => {
  clearNoOutputTimer();
  close();
});
</script>

<style scoped>
.command-stream {
  font-family: monospace;
  background: #191818;
  color: #fff;
  padding: 0 10px;
  height: 30vh;
  overflow-y: auto;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.terminal {
  white-space: pre-wrap;
}
</style>
