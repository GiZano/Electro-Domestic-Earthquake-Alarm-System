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
  userLocation: { latitude: number; longitude: number } | null;
  hasDismissedZoneBanner: boolean;
  setOfflineMode: (status: boolean) => void;
  toggleNotifications: () => void;
  dismissZoneBanner: () => void;
  setHomeZoneId: (zoneId: number | null) => void;
  setUserLocation: (loc: { latitude: number; longitude: number } | null) => void;
}

export const usePreferencesStore = create<PreferencesState>((set) => ({
  isOfflineMode: false,
  notificationsEnabled: true,
  homeZoneId: null,
  userLocation: null,
  hasDismissedZoneBanner: false,
  setOfflineMode: (status) => set({ isOfflineMode: status }),
  toggleNotifications: () => set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
  dismissZoneBanner: () => set({ hasDismissedZoneBanner: true }),
  setHomeZoneId: (zoneId) => set({ homeZoneId: zoneId }),
  setUserLocation: (loc) => set({ userLocation: loc }),
}));