import { create } from 'zustand';

interface PreferencesState {
  isOfflineMode: boolean;
  notificationsEnabled: boolean;
  /**
   * Operator's own area. When set, alarms (sound + vibration) are only raised
   * for alerts hitting this zone — a quake on the other side of the world
   * must not ring the phone. `null` = notify for every zone.
   */
  homeZoneId: number | null;
  setOfflineMode: (status: boolean) => void;
  toggleNotifications: () => void;
  setHomeZoneId: (zoneId: number | null) => void;
}

export const usePreferencesStore = create<PreferencesState>((set) => ({
  isOfflineMode: false,
  notificationsEnabled: true,
  homeZoneId: null,
  setOfflineMode: (status) => set({ isOfflineMode: status }),
  toggleNotifications: () => set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
  setHomeZoneId: (zoneId) => set({ homeZoneId: zoneId }),
}));