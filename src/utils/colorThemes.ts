/**
 * Color theme mapping for different article genres
 * Each genre gets a distinct color palette for visual distinction
 */

export interface ThemeColors {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  background: string;
  accent: string;
  text: string;
}

export const genreColorThemes: Record<string, ThemeColors> = {
  "AIツール": {
    primary: "#0066cc",
    primaryLight: "#cce5ff",
    primaryDark: "#0052a3",
    background: "#f0f6ff",
    accent: "#0088ff",
    text: "#003d7a",
  },
  "自動化ツール": {
    primary: "#cc3366",
    primaryLight: "#ffccdd",
    primaryDark: "#994455",
    background: "#fff0f5",
    accent: "#ff5588",
    text: "#7a1a3d",
  },
  "副業": {
    primary: "#ff9500",
    primaryLight: "#ffe5cc",
    primaryDark: "#cc7700",
    background: "#fff5e6",
    accent: "#ffaa22",
    text: "#7a4400",
  },
  "ガジェット": {
    primary: "#00aa44",
    primaryLight: "#ccf0dd",
    primaryDark: "#007722",
    background: "#f0f9f5",
    accent: "#00dd66",
    text: "#003d1a",
  },
  "ペット": {
    primary: "#ffcc00",
    primaryLight: "#fff5cc",
    primaryDark: "#cc9900",
    background: "#fffaf0",
    accent: "#ffdd44",
    text: "#7a6600",
  },
  "動物": {
    primary: "#ff8844",
    primaryLight: "#ffd9b3",
    primaryDark: "#cc6633",
    background: "#fff5f0",
    accent: "#ff9966",
    text: "#7a3d1a",
  },
  "植物": {
    primary: "#22aa44",
    primaryLight: "#ccf0dd",
    primaryDark: "#1a7d33",
    background: "#f0faf5",
    accent: "#44dd66",
    text: "#0d5a1f",
  },
  "食べ物": {
    primary: "#88aa22",
    primaryLight: "#d9e6b3",
    primaryDark: "#669900",
    background: "#fafef0",
    accent: "#aadd44",
    text: "#5a6b00",
  },
};

/**
 * Get the theme colors for a given genre
 * Defaults to AIツール theme if genre is not found
 */
export function getThemeColors(genre: string): ThemeColors {
  return genreColorThemes[genre] || genreColorThemes["AIツール"];
}

/**
 * Generate CSS custom properties from theme colors
 * For use in Astro components with style={`--primary: ${colors.primary}`} etc.
 */
export function generateThemeCSS(genre: string): string {
  const colors = getThemeColors(genre);
  return `
    --color-primary: ${colors.primary};
    --color-primary-light: ${colors.primaryLight};
    --color-primary-dark: ${colors.primaryDark};
    --color-background: ${colors.background};
    --color-accent: ${colors.accent};
    --color-text: ${colors.text};
  `;
}
