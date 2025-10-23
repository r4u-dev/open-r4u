import { useState, useEffect, useCallback } from 'react';

interface ColorPalette {
  name: string;
  description: string;
  colors: {
    [key: string]: string;
  };
}

const colorPalettes: ColorPalette[] = [
  {
    name: "Tech Blue (Current)",
    description: "Professional tech dashboard with performance focus",
    colors: {
      "--primary": "214 84% 56%",
      "--primary-hover": "214 84% 48%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "210 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Slate & Orange",
    description: "Modern sophisticated with warm orange accents",
    colors: {
      "--primary": "15 86% 53%",
      "--primary-hover": "15 86% 45%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "15 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Purple Gradient",
    description: "Modern creative with purple-to-magenta theme",
    colors: {
      "--primary": "271 91% 65%",
      "--primary-hover": "271 91% 57%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "270 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Green Tech",
    description: "Developer-focused with neon green highlights",
    colors: {
      "--primary": "142 84% 47%",
      "--primary-hover": "142 84% 39%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "142 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Rose & Gold",
    description: "Elegant premium with rose gold accents",
    colors: {
      "--primary": "350 89% 67%",
      "--primary-hover": "350 89% 59%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "350 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Sage Green & Cream",
    description: "Calming nature-inspired palette",
    colors: {
      "--primary": "123 38% 57%",
      "--primary-hover": "123 38% 49%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "123 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Coral & Navy",
    description: "Warm yet professional combination",
    colors: {
      "--primary": "16 100% 66%",
      "--primary-hover": "16 100% 58%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "16 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Indigo & Teal",
    description: "Professional yet approachable",
    colors: {
      "--primary": "262 83% 58%",
      "--primary-hover": "262 83% 50%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "262 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Crimson & Charcoal",
    description: "Bold and striking for high-impact applications",
    colors: {
      "--primary": "0 72% 51%",
      "--primary-hover": "0 72% 43%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "0 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Amber & Deep Blue",
    description: "Warm accent with cool professional base",
    colors: {
      "--primary": "45 93% 47%",
      "--primary-hover": "45 93% 39%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "45 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Lavender & Silver",
    description: "Soft and sophisticated with metallic touches",
    colors: {
      "--primary": "270 95% 80%",
      "--primary-hover": "270 95% 72%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "270 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "Forest & Copper",
    description: "Earthy and rich with copper highlights",
    colors: {
      "--primary": "25 95% 53%",
      "--primary-hover": "25 95% 45%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--accent": "25 17% 95%",
      "--background": "0 0% 100%",
      "--foreground": "222.2 84% 4.9%",
      "--card": "0 0% 100%",
      "--card-foreground": "222.2 84% 4.9%",
      "--muted": "210 40% 98%",
      "--muted-foreground": "215.4 16.3% 46.9%",
      "--border": "214.3 31.8% 91.4%",
    }
  },
  {
    name: "One Dark",
    description: "Developer favorite with cool blue accents",
    colors: {
      "--primary": "207 82% 66%",
      "--primary-hover": "207 82% 58%",
      "--success": "95 38% 62%",
      "--warning": "39 67% 69%",
      "--destructive": "5 48% 51%",
      "--accent": "207 17% 95%",
      "--background": "222.2 84% 4.9%",
      "--foreground": "210 40% 98%",
      "--card": "222.2 84% 4.9%",
      "--card-foreground": "210 40% 98%",
      "--muted": "217.2 32.6% 17.5%",
      "--muted-foreground": "215 20.2% 65.1%",
      "--border": "217.2 32.6% 17.5%",
    }
  },
  // Dark Mode Palettes
  {
    name: "Midnight Blue (Dark)",
    description: "Deep tech theme perfect for dark mode environments",
    colors: {
      "--primary": "214 84% 56%",
      "--primary-hover": "214 84% 48%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "215 16% 12%",
      "--foreground": "210 17% 95%",
      "--card": "215 16% 15%",
      "--card-foreground": "210 17% 95%",
      "--muted": "215 16% 16%",
      "--muted-foreground": "215 10% 60%",
      "--border": "215 16% 18%",
    }
  },
  {
    name: "Dark Orange (Dark)",
    description: "Sophisticated dark theme with vibrant orange accents",
    colors: {
      "--primary": "15 86% 53%",
      "--primary-hover": "15 86% 45%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "15 8% 8%",
      "--foreground": "15 17% 95%",
      "--card": "15 8% 12%",
      "--card-foreground": "15 17% 95%",
      "--muted": "15 8% 10%",
      "--muted-foreground": "15 10% 60%",
      "--border": "15 8% 15%",
    }
  },
  {
    name: "Violet Night (Dark)",
    description: "Mysterious dark theme with deep purple undertones",
    colors: {
      "--primary": "271 91% 65%",
      "--primary-hover": "271 91% 57%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "271 15% 8%",
      "--foreground": "271 17% 95%",
      "--card": "271 15% 12%",
      "--card-foreground": "271 17% 95%",
      "--muted": "271 15% 10%",
      "--muted-foreground": "271 10% 60%",
      "--border": "271 15% 15%",
    }
  },
  {
    name: "Forest Dark (Dark)",
    description: "Dark forest theme with deep green undertones",
    colors: {
      "--primary": "142 76% 36%",
      "--primary-hover": "142 76% 28%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "142 15% 8%",
      "--foreground": "142 17% 95%",
      "--card": "142 15% 12%",
      "--card-foreground": "142 17% 95%",
      "--muted": "142 15% 10%",
      "--muted-foreground": "142 10% 60%",
      "--border": "142 15% 15%",
    }
  },
  {
    name: "Ocean Deep (Dark)",
    description: "Deep ocean theme with midnight blue tones",
    colors: {
      "--primary": "200 100% 50%",
      "--primary-hover": "200 100% 42%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "200 15% 8%",
      "--foreground": "200 17% 95%",
      "--card": "200 15% 12%",
      "--card-foreground": "200 17% 95%",
      "--muted": "200 15% 10%",
      "--muted-foreground": "200 10% 60%",
      "--border": "200 15% 15%",
    }
  },
  {
    name: "Blood Moon (Dark)",
    description: "Dramatic dark theme with crimson accents",
    colors: {
      "--primary": "348 83% 47%",
      "--primary-hover": "348 83% 39%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "348 15% 8%",
      "--foreground": "348 17% 95%",
      "--card": "348 15% 12%",
      "--card-foreground": "348 17% 95%",
      "--muted": "348 15% 10%",
      "--muted-foreground": "348 10% 60%",
      "--border": "348 15% 15%",
    }
  },
  {
    name: "Golden Night (Dark)",
    description: "Rich dark theme with golden amber highlights",
    colors: {
      "--primary": "43 96% 56%",
      "--primary-hover": "43 96% 48%",
      "--success": "142 76% 36%",
      "--warning": "38 92% 50%",
      "--destructive": "0 84% 60%",
      "--background": "43 15% 6%",
      "--foreground": "43 17% 95%",
      "--card": "43 15% 10%",
      "--card-foreground": "43 17% 95%",
      "--muted": "43 15% 8%",
      "--muted-foreground": "43 10% 60%",
      "--border": "43 15% 12%",
    }
  }
];

const THEME_STORAGE_KEY = 'r4u-theme-palette';
const DEFAULT_THEME_NAME = 'Dark Orange (Dark)';
const DEFAULT_THEME_INDEX = Math.max(
  0,
  colorPalettes.findIndex((p) => p.name === DEFAULT_THEME_NAME)
);

export const useTheme = () => {
  const [selectedPalette, setSelectedPalette] = useState<number>(DEFAULT_THEME_INDEX);
  const [isInitialized, setIsInitialized] = useState(false);

  // Apply palette to CSS custom properties
  const applyPalette = useCallback((palette: ColorPalette) => {
    const root = document.documentElement;
    Object.entries(palette.colors).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });
  }, []);

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedThemeIndex = localStorage.getItem(THEME_STORAGE_KEY);
    if (savedThemeIndex !== null) {
      const index = parseInt(savedThemeIndex, 10);
      if (index >= 0 && index < colorPalettes.length) {
        setSelectedPalette(index);
        applyPalette(colorPalettes[index]);
        setIsInitialized(true);
        return;
      }
    }

    // No saved theme; apply and persist the default
    setSelectedPalette(DEFAULT_THEME_INDEX);
    applyPalette(colorPalettes[DEFAULT_THEME_INDEX]);
    localStorage.setItem(THEME_STORAGE_KEY, DEFAULT_THEME_INDEX.toString());
    setIsInitialized(true);
  }, [applyPalette]);

  // Change theme and persist to localStorage
  const changeTheme = useCallback((paletteIndex: number) => {
    if (paletteIndex >= 0 && paletteIndex < colorPalettes.length) {
      setSelectedPalette(paletteIndex);
      applyPalette(colorPalettes[paletteIndex]);
      localStorage.setItem(THEME_STORAGE_KEY, paletteIndex.toString());
    }
  }, [applyPalette]);

  // Get current palette
  const getCurrentPalette = useCallback(() => {
    return colorPalettes[selectedPalette];
  }, [selectedPalette]);

  return {
    colorPalettes,
    selectedPalette,
    changeTheme,
    getCurrentPalette,
    isInitialized,
  };
};