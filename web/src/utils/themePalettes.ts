import { setCssVar, Dark } from "quasar";
import { ref } from "vue";

export interface ThemePalette {
  id: string;
  name: string;
  subtitle: string;
  group: "dark" | "light";
  isDark: boolean;
  swatches: [string, string, string, string, string];
  bg: string;
  surface: string;
  headerBg: string;
  tableHeaderBg: string;
  rowHoverBg: string;
  rowActiveBg: string;
  primary: string;
  secondary: string;
  textPrimary: string;
  textSecondary: string;
  border: string;
}

export const THEME_PALETTES: ThemePalette[] = [
  {
    id: "classic-dark",
    name: "Padrão Tactical (Grafite)",
    subtitle: "Tema escuro clássico de alto contraste do Tactical RMM",
    group: "dark",
    isDark: true,
    swatches: ["#121212", "#1D1D1D", "#1976D2", "#26A69A", "#F5F5F5"],
    bg: "#121212",
    surface: "#1D1D1D",
    headerBg: "#1F242D",
    tableHeaderBg: "#181B20",
    rowHoverBg: "rgba(25, 118, 210, 0.16)",
    rowActiveBg: "#263244",
    primary: "#1976D2",
    secondary: "#26A69A",
    textPrimary: "#FFFFFF",
    textSecondary: "#B0BEC5",
    border: "rgba(255, 255, 255, 0.12)",
  },
  {
    id: "cobalt-executive",
    name: "Azul Cobalto Executivo",
    subtitle: "Azul-marinho profundo com destaque corporativo nítido (NOC / TI)",
    group: "dark",
    isDark: true,
    swatches: ["#0B1120", "#131C31", "#2563EB", "#38BDF8", "#F1F5F9"],
    bg: "#0B1120",
    surface: "#131C31",
    headerBg: "#172542",
    tableHeaderBg: "#11192C",
    rowHoverBg: "rgba(37, 99, 235, 0.18)",
    rowActiveBg: "#1D3461",
    primary: "#2563EB",
    secondary: "#38BDF8",
    textPrimary: "#F1F5F9",
    textSecondary: "#94A3B8",
    border: "rgba(148, 163, 184, 0.18)",
  },
  {
    id: "clinical-emerald",
    name: "Esmeralda Clínica (Hospitalar)",
    subtitle: "Petróleo escuro e verde-água clínico de alta legibilidade",
    group: "dark",
    isDark: true,
    swatches: ["#0B1517", "#122326", "#0D9488", "#2DD4BF", "#F0FDFA"],
    bg: "#0B1517",
    surface: "#122326",
    headerBg: "#133036",
    tableHeaderBg: "#0F1E21",
    rowHoverBg: "rgba(13, 148, 136, 0.20)",
    rowActiveBg: "#164348",
    primary: "#0D9488",
    secondary: "#2DD4BF",
    textPrimary: "#F0FDFA",
    textSecondary: "#99D5CE",
    border: "rgba(45, 212, 191, 0.18)",
  },
  {
    id: "slate-indigo",
    name: "Ardósia & Índigo Moderno",
    subtitle: "Cinza ardósia equilibrado com acento índigo moderno",
    group: "dark",
    isDark: true,
    swatches: ["#0F172A", "#1E293B", "#4F46E5", "#818CF8", "#F8FAFC"],
    bg: "#0F172A",
    surface: "#1E293B",
    headerBg: "#243247",
    tableHeaderBg: "#162033",
    rowHoverBg: "rgba(99, 102, 241, 0.18)",
    rowActiveBg: "#2B3A67",
    primary: "#4F46E5",
    secondary: "#818CF8",
    textPrimary: "#F8FAFC",
    textSecondary: "#CBD5E1",
    border: "rgba(148, 163, 184, 0.20)",
  },
  {
    id: "forest-night",
    name: "Floresta Noturna",
    subtitle: "Verde escuro sóbrio e confortável para longas jornadas",
    group: "dark",
    isDark: true,
    swatches: ["#0D1512", "#16231D", "#15803D", "#4ADE80", "#F0FDF4"],
    bg: "#0D1512",
    surface: "#16231D",
    headerBg: "#1B2E25",
    tableHeaderBg: "#121E19",
    rowHoverBg: "rgba(22, 163, 74, 0.18)",
    rowActiveBg: "#1F3B2D",
    primary: "#15803D",
    secondary: "#4ADE80",
    textPrimary: "#F0FDF4",
    textSecondary: "#A7C4B5",
    border: "rgba(74, 222, 128, 0.18)",
  },
  {
    id: "classic-light",
    name: "Modo Claro Corporativo",
    subtitle: "Fundo claro limpo de alto contraste para apresentações",
    group: "light",
    isDark: false,
    swatches: ["#F8FAFC", "#FFFFFF", "#0284C7", "#0F766E", "#0F172A"],
    bg: "#F8FAFC",
    surface: "#FFFFFF",
    headerBg: "#0F172A",
    tableHeaderBg: "#F1F5F9",
    rowHoverBg: "rgba(2, 132, 199, 0.08)",
    rowActiveBg: "#DBEAFE",
    primary: "#0284C7",
    secondary: "#0F766E",
    textPrimary: "#0F172A",
    textSecondary: "#475569",
    border: "rgba(15, 23, 42, 0.12)",
  },
];

const LEGACY_PALETTE_MAP: Record<string, string> = {
  "salvia-concreta": "forest-night",
  "carvao-cobalto": "cobalt-executive",
  "lavanda-aco": "slate-indigo",
  "forest-minimal": "forest-night",
  "seafoam-slate": "clinical-emerald",
  "teal-studio": "clinical-emerald",
};

const STORAGE_KEY = "trmm_active_theme_palette";

function resolvePaletteId(rawId?: string | null): string {
  const cleaned = String(rawId || "").trim();
  if (!cleaned) return "classic-dark";
  const mapped = LEGACY_PALETTE_MAP[cleaned] || cleaned;
  return THEME_PALETTES.some((p) => p.id === mapped) ? mapped : "classic-dark";
}

export const currentPaletteId = ref<string>(
  resolvePaletteId(typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null),
);

let styleElement: HTMLStyleElement | null = null;

export function applyThemePalette(paletteId: string): void {
  const resolvedId = resolvePaletteId(paletteId);
  const palette =
    THEME_PALETTES.find((p) => p.id === resolvedId) || THEME_PALETTES[0];
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

  if (!palette.isDark) {
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
      body.body--light .q-bar:not(.bg-teal-10):not(.bg-primary):not(.bg-indigo-9) {
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
        background-color: ${palette.tableHeaderBg} !important;
        color: ${palette.textPrimary} !important;
        border-color: ${palette.border} !important;
      }
      body.body--light .q-table tbody td {
        border-color: ${palette.border} !important;
        color: ${palette.textPrimary} !important;
      }
      body.body--light .q-table tbody tr:hover {
        background-color: ${palette.rowHoverBg} !important;
      }
      body.body--light .q-table tbody tr.highlight {
        background-color: ${palette.rowActiveBg} !important;
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
    body.body--dark .q-bar:not(.bg-teal-10):not(.bg-primary):not(.bg-indigo-9) {
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
      background-color: ${palette.tableHeaderBg} !important;
      color: ${palette.textPrimary} !important;
      border-color: ${palette.border} !important;
    }
    body.body--dark .q-table tbody td {
      border-color: ${palette.border} !important;
      color: ${palette.textPrimary} !important;
    }
    body.body--dark .q-table tbody tr:hover {
      background-color: ${palette.rowHoverBg} !important;
    }
    body.body--dark .q-table tbody tr.highlight-dark {
      background-color: ${palette.rowActiveBg} !important;
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
