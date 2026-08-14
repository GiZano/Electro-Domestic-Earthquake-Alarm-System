import { useThemeStore } from "../store/useThemeStore";
import { THEMES } from "../theme";

beforeEach(() => {
  useThemeStore.setState({ themeMode: "dark" });
});

describe("useThemeStore", () => {
  it("starts in MIC (dark) mode", () => {
    expect(useThemeStore.getState().themeMode).toBe("dark");
  });

  it("toggles between dark and light", () => {
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().themeMode).toBe("light");

    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().themeMode).toBe("dark");
  });

  it("sets mode explicitly", () => {
    useThemeStore.getState().setThemeMode("light");
    expect(useThemeStore.getState().themeMode).toBe("light");
  });

  it("both palettes exist and differ", () => {
    expect(THEMES.dark.bg).not.toBe(THEMES.light.bg);
    expect(THEMES.dark.text).not.toBe(THEMES.light.text);
  });
});