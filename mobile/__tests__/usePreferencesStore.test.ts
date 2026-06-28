import { usePreferencesStore } from "../store/usePreferencesStore";

beforeEach(() => {
  usePreferencesStore.setState({
    isOfflineMode: false,
    notificationsEnabled: true,
  });
});

describe("usePreferencesStore", () => {
  it("starts online with notifications enabled", () => {
    const state = usePreferencesStore.getState();
    expect(state.isOfflineMode).toBe(false);
    expect(state.notificationsEnabled).toBe(true);
  });

  it("toggles offline mode", () => {
    usePreferencesStore.getState().setOfflineMode(true);
    expect(usePreferencesStore.getState().isOfflineMode).toBe(true);

    usePreferencesStore.getState().setOfflineMode(false);
    expect(usePreferencesStore.getState().isOfflineMode).toBe(false);
  });

  it("toggles notifications", () => {
    usePreferencesStore.getState().toggleNotifications();
    expect(usePreferencesStore.getState().notificationsEnabled).toBe(false);

    usePreferencesStore.getState().toggleNotifications();
    expect(usePreferencesStore.getState().notificationsEnabled).toBe(true);
  });
});
