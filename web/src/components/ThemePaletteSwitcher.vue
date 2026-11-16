<template>
  <q-btn
    dense
    flat
    no-caps
    icon="palette"
    class="q-mr-xs"
    data-no-translate="true"
  >
    <q-tooltip>Temas &amp; Paletas de Cores</q-tooltip>
    <q-menu style="min-width: 310px; max-width: 360px" data-no-translate="true">
      <q-list dense separator>
        <q-item-label header class="text-weight-bold row items-center">
          <q-icon name="palette" color="primary" size="sm" class="q-mr-xs" />
          Paletas de Cores &amp; Temas
        </q-item-label>

        <q-item
          v-for="pal in palettes"
          :key="pal.id"
          clickable
          v-ripple
          :active="currentPaletteId === pal.id"
          active-class="bg-grey-9 text-white"
          @click="selectPalette(pal.id)"
          class="q-py-sm"
        >
          <q-item-section>
            <q-item-label class="text-weight-bold row items-center justify-between">
              <span>{{ pal.name }}</span>
              <q-icon
                v-if="currentPaletteId === pal.id"
                name="check_circle"
                color="positive"
                size="xs"
              />
            </q-item-label>
            <div class="row no-wrap q-mt-xs" style="border-radius: 6px; overflow: hidden; height: 22px; border: 1px solid rgba(255,255,255,0.2)">
              <div
                v-for="(hex, idx) in pal.swatches"
                :key="idx"
                :style="{ backgroundColor: hex, flex: 1 }"
                :title="hex"
              />
            </div>
            <q-item-label caption class="q-mt-xs" style="font-size: 10px; opacity: 0.8">
              {{ pal.subtitle }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-menu>
  </q-btn>
</template>

<script setup lang="ts">
import { THEME_PALETTES, currentPaletteId, applyThemePalette } from "@/utils/themePalettes";
import { notifySuccess } from "@/utils/notify";

const palettes = THEME_PALETTES;

function selectPalette(id: string) {
  applyThemePalette(id);
  const found = palettes.find((p) => p.id === id);
  if (found) {
    notifySuccess(`Tema aplicado: ${found.name}`);
  }
}
</script>
