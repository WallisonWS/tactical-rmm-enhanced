import { setCssVar, Dark } from "quasar";
import { ref } from "vue";

export interface ThemePalette {
  id: string;
  name: string;
  subtitle: string;
  isDark: boolean;
  swatches: [string, string, string, string, string];
  bg: string;
  surface: string;
  headerBg: string;
  primary: string;
  secondary: string;
  textPrimary: string;
  textSecondary: string;
  border: string;
}

export const THEME_PALETTES: ThemePalette[] = [
  {
    id: "classic-dark",
    name: "Padrão Tactical (Escuro)",
    subtitle: "Tema original escuro do Tactical RMM",
    isDark: true,
    swatches: ["#121212", "#1D1D1D", "#1976D2", "#26A69A", "#F5F5F5"],
    bg: "#121212",
    surface: "#1D1D1D",
    headerBg: "#212121",
    primary: "#1976D2",
    secondary: "#26A69A",
    textPrimary: "#FFFFFF",
    textSecondary: "#B0BEC5",
    border: "rgba(255,255,255,0.12)",
  },
  {
    id: "salvia-concreta",
    name: "1) Sálvia Concreta",
    subtitle: "#1F2328 • #3C4A3F • #A9B7A6 • #E7E2D9 • #C97C5D",
    isDark: true,
    swatches: ["#1F2328", "#3C4A3F", "#A9B7A6", "#E7E2D9", "#C97C5D"],
    bg: "#1F2328",
    surface: "#28312B",
    headerBg: "#3C4A3F",
    primary: "#C97C5D",
    secondary: "#A9B7A6",
    textPrimary: "#E7E2D9",
    textSecondary: "#A9B7A6",
    border: "rgba(169, 183, 166, 0.22)",
  },
  {
    id: "carvao-cobalto",
    name: "4) Carvão Cobalto",
    subtitle: "#0F1115 • #2B2F3A • #1F5EFF • #CFD6E6 • #F2F5FF",
    isDark: true,
    swatches: ["#0F1115", "#2B2F3A", "#1F5EFF", "#CFD6E6", "#F2F5FF"],
    bg: "#0F1115",
    surface: "#1B1E26",
    headerBg: "#2B2F3A",
    primary: "#1F5EFF",
    secondary: "#CFD6E6",
    textPrimary: "#F2F5FF",
    textSecondary: "#CFD6E6",
    border: "rgba(207, 214, 230, 0.18)",
  },
  {
    id: "lavanda-aco",
    name: "8) Lavanda Aço",
    subtitle: "#1B1D23 • #515563 • #A6A0C4 • #D9D6EE • #F4F3FB",
    isDark: true,
    swatches: ["#1B1D23", "#515563", "#A6A0C4", "#D9D6EE", "#F4F3FB"],
    bg: "#1B1D23",
    surface: "#282B34",
    headerBg: "#515563",
    primary: "#A6A0C4",
    secondary: "#D9D6EE",
    textPrimary: "#F4F3FB",
    textSecondary: "#D9D6EE",
    border: "rgba(166, 160, 196, 0.24)",
  },
  {
    id: "forest-minimal",
    name: "11) Forest Minimal",
    subtitle: "#0F1411 • #263A2E • #4F6F5A • #D8E1D7 • #F3F6F2",
    isDark: true,
    swatches: ["#0F1411", "#263A2E", "#4F6F5A", "#D8E1D7", "#F3F6F2"],
    bg: "#0F1411",
    surface: "#18241D",
    headerBg: "#263A2E",
    primary: "#4F6F5A",
    secondary: "#D8E1D7",
    textPrimary: "#F3F6F2",
    textSecondary: "#D8E1D7",
    border: "rgba(79, 111, 90, 0.28)",
  },
  {
    id: "seafoam-slate",
    name: "13) Seafoam Slate",
    subtitle: "#12181B • #3F5A60 • #7FC8C2 • #D9F0EE • #F6FBFB",
    isDark: true,
    swatches: ["#12181B", "#3F5A60", "#7FC8C2", "#D9F0EE", "#F6FBFB"],
    bg: "#12181B",
    surface: "#1E292E",
    headerBg: "#3F5A60",
    primary: "#7FC8C2",
    secondary: "#D9F0EE",
    textPrimary: "#F6FBFB",
    textSecondary: "#D9F0EE",
    border: "rgba(127, 200, 194, 0.24)",
  },
  {
    id: "teal-studio",
    name: "16) Teal Studio",
    subtitle: "#0D1416 • #1B3B40 • #2B7C85 • #BFE7EA • #F2FBFB",
    isDark: true,
    swatches: ["#0D1416", "#1B3B40", "#2B7C85", "#BFE7EA", "#F2FBFB"],
    bg: "#0D1416",
    surface: "#13262A",
    headerBg: "#1B3B40",
    primary: "#2B7C85",
    secondary: "#BFE7EA",
    textPrimary: "#F2FBFB",
    textSecondary: "#BFE7EA",
    border: "rgba(43, 124, 133, 0.28)",
  },
  {
    id: "classic-light",
    name: "Modo Claro Corporativo",
    subtitle: "Fundo claro de alto contraste",
    isDark: false,
    swatches: ["#F8FAFC", "#FFFFFF", "#0284C7", "#E2E8F0", "#0F172A"],
    bg: "#F8FAFC",
    surface: "#FFFFFF",
    headerBg: "#1E293B",
    primary: "#0284C7",
    secondary: "#475569",
    textPrimary: "#0F172A",
    textSecondary: "#475569",
    border: "rgba(15, 23, 42, 0.12)",
  },
];

const STORAGE_KEY = "trmm_active_theme_palette";
export const currentPaletteId = ref<string>(
  (typeof localStorage !== "undefined" && localStorage.getItem(STORAGE_KEY)) || "classic-dark",
);

let styleElement: HTMLStyleElement | null = null;

export function applyThemePalette(paletteId: string): void {
  const palette =
    THEME_PALETTES.find((p) => p.id === paletteId) || THEME_PALETTES[0];
  currentPaletteId.value = palette.id;

  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, palette.id);
  }

  Dark.set(palette.isDark);
  setCssVar("primary", palette.primary);
  setCssVar("secondary", palette.secondary);
  setCssVar("dark", palette.surface);
  setCssVar("dark-page", palette.bg);

  if (typeof document === "undefined") return;

  const root = document.documentElement;
  root.style.setProperty("--trmm-bg", palette.bg);
  root.style.setProperty("--trmm-surface", palette.surface);
  root.style.setProperty("--trmm-header-bg", palette.headerBg);
  root.style.setProperty("--trmm-primary", palette.primary);
  root.style.setProperty("--trmm-secondary", palette.secondary);
  root.style.setProperty("--trmm-text", palette.textPrimary);
  root.style.setProperty("--trmm-text-muted", palette.textSecondary);
  root.style.setProperty("--trmm-border", palette.border);

  if (!styleElement) {
    styleElement = document.createElement("style");
    styleElement.id = "trmm-custom-palette-styles";
    document.head.appendChild(styleElement);
  }

  if (palette.id === "classic-dark") {
    styleElement.textContent = "";
    return;
  }

  if (palette.id === "classic-light") {
    styleElement.textContent = `
      body.body--light {
        background-color: ${palette.bg} !important;
        color: ${palette.textPrimary} !important;
      }
      body.body--light .q-page,
      body.body--light .q-page-container,
      body.body--light .q-splitter__panel {
        background-color: ${palette.bg} !important;
        color: ${palette.textPrimary} !important;
      }
      body.body--light .q-header {
        background: ${palette.headerBg} !important;
        color: #FFFFFF !important;
        border-bottom: 1px solid ${palette.border} !important;
      }
      body.body--light .q-bar {
        background: #E2E8F0 !important;
        color: ${palette.textPrimary} !important;
        border-bottom: 1px solid ${palette.border} !important;
      }
      body.body--light .q-card,
      body.body--light .q-dialog__inner .q-card,
      body.body--light .q-menu,
      body.body--light .q-table__card,
      body.body--light .q-tab-panels,
      body.body--light .q-tab-panel {
        background-color: ${palette.surface} !important;
        color: ${palette.textPrimary} !important;
      }
      body.body--light .q-table thead tr,
      body.body--light .q-table th {
        background-color: #F1F5F9 !important;
        color: ${palette.textPrimary} !important;
        border-color: ${palette.border} !important;
      }
      body.body--light .q-table tbody td {
        border-color: ${palette.border} !important;
        color: ${palette.textPrimary} !important;
      }
      body.body--light .q-separator {
        background: ${palette.border} !important;
      }
      body.body--light .text-primary {
        color: ${palette.primary} !important;
      }
      body.body--light .bg-primary {
        background: ${palette.primary} !important;
      }
    `;
    return;
  }

  styleElement.textContent = `
    body.body--dark {
      background-color: ${palette.bg} !important;
      color: ${palette.textPrimary} !important;
    }
    body.body--dark .q-page,
    body.body--dark .q-page-container,
    body.body--dark .q-splitter__panel {
      background-color: ${palette.bg} !important;
      color: ${palette.textPrimary} !important;
    }
    body.body--dark .q-header {
      background: ${palette.headerBg} !important;
      border-bottom: 1px solid ${palette.border} !important;
    }
    body.body--dark .q-bar {
      background: ${palette.surface} !important;
      color: ${palette.textPrimary} !important;
      border-bottom: 1px solid ${palette.border} !important;
    }
    body.body--dark .q-card,
    body.body--dark .q-dialog__inner .q-card,
    body.body--dark .q-menu,
    body.body--dark .q-table__card,
    body.body--dark .q-tab-panels,
    body.body--dark .q-tab-panel {
      background-color: ${palette.surface} !important;
      color: ${palette.textPrimary} !important;
    }
    body.body--dark .q-field--outlined .q-field__control:before,
    body.body--dark .q-splitter__separator {
      border-color: ${palette.border} !important;
    }
    body.body--dark .q-table thead tr,
    body.body--dark .q-table th {
      background-color: ${palette.headerBg} !important;
      color: ${palette.textPrimary} !important;
      border-color: ${palette.border} !important;
    }
    body.body--dark .q-table tbody td {
      border-color: ${palette.border} !important;
      color: ${palette.textPrimary} !important;
    }
    body.body--dark .q-table tbody tr.highlight-dark {
      background-color: ${palette.headerBg} !important;
    }
    body.body--dark .q-separator {
      background: ${palette.border} !important;
    }
    body.body--dark .text-primary {
      color: ${palette.primary} !important;
    }
    body.body--dark .bg-primary {
      background: ${palette.primary} !important;
    }
  `;
}

export function initSavedThemePalette(): void {
  if (typeof localStorage !== "undefined") {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      applyThemePalette(saved);
    }
  }
}

export function syncDarkModeWithSavedPalette(apiDarkMode: boolean): void {
  if (typeof localStorage !== "undefined") {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      applyThemePalette(saved);
      return;
    }
  }
  applyThemePalette(apiDarkMode ? "classic-dark" : "classic-light");
}

export function toggleLightDarkWithPalette(dark: boolean): void {
  if (!dark) {
    applyThemePalette("classic-light");
    return;
  }
  const current = THEME_PALETTES.find((p) => p.id === currentPaletteId.value);
  applyThemePalette(current && current.isDark ? current.id : "classic-dark");
}
