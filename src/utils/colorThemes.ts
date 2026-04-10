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
    primary: "#0088dd",
    primaryLight: "#cce0ff",
    primaryDark: "#0055aa",
    background: "#f0f5ff",
    accent: "#00aaff",
    text: "#003d8a",
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
  "生活改善": {
    primary: "#9966ff",
    primaryLight: "#ede5ff",
    primaryDark: "#6633cc",
    background: "#f5f0ff",
    accent: "#bb88ff",
    text: "#4d2e99",
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
