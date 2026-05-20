import { create } from 'zustand';

interface PreferencesState {
  isOfflineMode: boolean;
  notificationsEnabled: boolean;
  setOfflineMode: (status: boolean) => void;
  toggleNotifications: () => void;
}

export const usePreferencesStore = create<PreferencesState>((set) => ({
  isOfflineMode: false,
  notificationsEnabled: true,
  setOfflineMode: (status) => set({ isOfflineMode: status }),
  toggleNotifications: () => set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
}));