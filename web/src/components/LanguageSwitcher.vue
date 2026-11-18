<template>
  <q-btn
    dense
    flat
    no-caps
    class="q-mr-xs trmm-lang-btn"
    data-no-translate="true"
  >
    <div class="row items-center no-wrap q-gutter-x-xs">
      <span class="trmm-flag-wrap" v-html="flagSvg(activeLocaleOption.code)" />
      <span class="text-weight-bold" style="font-size: 12px; letter-spacing: 0.3px">
        {{ activeLocaleOption.shortLabel }}
      </span>
      <q-icon name="expand_more" size="15px" style="opacity: 0.8" />
    </div>
    <q-tooltip :delay="350">{{ t("nav.language") }}</q-tooltip>

    <q-menu
      auto-close
      style="min-width: 235px; border-radius: 10px"
      data-no-translate="true"
    >
      <q-list dense class="q-py-xs">
        <q-item-label header class="text-weight-bold row items-center q-py-sm">
          <q-icon name="translate" color="primary" size="18px" class="q-mr-xs" />
          <span>{{ t("nav.language") }}</span>
        </q-item-label>
        <q-separator class="q-mb-xs" />

        <q-item
          v-for="opt in locales"
          :key="opt.code"
          clickable
          v-ripple
          v-close-popup
          class="q-mx-xs q-my-xs rounded-borders trmm-lang-item"
          :class="{ 'trmm-lang-item--active': locale === opt.code }"
          @click="selectLanguage(opt.code)"
        >
          <q-item-section avatar style="min-width: 34px; padding-right: 8px">
            <span class="trmm-flag-wrap trmm-flag-wrap--lg" v-html="flagSvg(opt.code)" />
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-bold" style="font-size: 13px">
              {{ opt.label }}
            </q-item-label>
            <q-item-label caption style="font-size: 10px; opacity: 0.72">
              {{ regionHint(opt.code) }}
            </q-item-label>
          </q-item-section>
          <q-item-section side v-if="locale === opt.code">
            <q-icon name="check_circle" size="17px" color="positive" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-menu>
  </q-btn>
</template>

<script setup lang="ts">
import { useI18n, type SupportedLocale } from "@/i18n";
import { notifySuccess } from "@/utils/notify";

const { locale, locales, activeLocaleOption, setLocale, t } = useI18n();

function flagSvg(code: SupportedLocale): string {
  if (code === "pt-BR") {
    return `<svg viewBox="0 0 24 16" width="20" height="14" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="24" height="16" fill="#009B3A"/>
      <polygon points="12,1.8 21.6,8 12,14.2 2.4,8" fill="#FFDF00"/>
      <circle cx="12" cy="8" r="3.6" fill="#002776"/>
      <path d="M8.6,7.4 C10.6,6.8 13.4,7.2 15.4,8.7" stroke="#FFFFFF" stroke-width="0.7" fill="none"/>
    </svg>`;
  }
  if (code === "en-US") {
    return `<svg viewBox="0 0 24 16" width="20" height="14" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="24" height="16" fill="#FFFFFF"/>
      <rect y="0" width="24" height="1.25" fill="#B22234"/>
      <rect y="2.5" width="24" height="1.25" fill="#B22234"/>
      <rect y="5" width="24" height="1.25" fill="#B22234"/>
      <rect y="7.5" width="24" height="1.25" fill="#B22234"/>
      <rect y="10" width="24" height="1.25" fill="#B22234"/>
      <rect y="12.5" width="24" height="1.25" fill="#B22234"/>
      <rect y="14.8" width="24" height="1.2" fill="#B22234"/>
      <rect width="10.2" height="8.7" fill="#3C3B6E"/>
      <circle cx="2.2" cy="2" r="0.55" fill="#FFF"/>
      <circle cx="5.1" cy="2" r="0.55" fill="#FFF"/>
      <circle cx="8" cy="2" r="0.55" fill="#FFF"/>
      <circle cx="3.6" cy="4.2" r="0.55" fill="#FFF"/>
      <circle cx="6.6" cy="4.2" r="0.55" fill="#FFF"/>
      <circle cx="2.2" cy="6.5" r="0.55" fill="#FFF"/>
      <circle cx="5.1" cy="6.5" r="0.55" fill="#FFF"/>
      <circle cx="8" cy="6.5" r="0.55" fill="#FFF"/>
    </svg>`;
  }
  return `<svg viewBox="0 0 24 16" width="20" height="14" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect width="24" height="16" fill="#AA151B"/>
    <rect y="4" width="24" height="8" fill="#F1BF00"/>
    <rect x="6" y="6.2" width="2.6" height="3.6" rx="0.5" fill="#AA151B"/>
  </svg>`;
}

function regionHint(code: SupportedLocale): string {
  if (code === "pt-BR") return "Brasil • PT-BR";
  if (code === "en-US") return "United States • EN-US";
  return "Español • ES-ES";
}

function selectLanguage(code: SupportedLocale) {
  setLocale(code);
  const chosen = locales.find((l) => l.code === code);
  if (chosen) {
    notifySuccess(`${t("nav.language")}: ${chosen.label}`);
  }
}
</script>

<style scoped>
.trmm-lang-btn {
  border-radius: 7px;
  padding: 2px 8px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  transition: all 0.15s ease;
}
.trmm-lang-btn:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.32);
}
.trmm-flag-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.25);
  line-height: 0;
}
.trmm-flag-wrap--lg {
  transform: scale(1.15);
}
.trmm-lang-item {
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.trmm-lang-item:hover {
  border-color: rgba(56, 189, 248, 0.35);
}
.trmm-lang-item--active {
  border-color: var(--q-primary, #1976d2);
  background: rgba(25, 118, 210, 0.16);
}
</style>
