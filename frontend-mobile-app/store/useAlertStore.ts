import { create } from 'zustand';
import { AlertMessage } from '../context/WebSocketContext';

interface AlertStoreState {
  alerts: AlertMessage[];
  addAlert: (alert: AlertMessage) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertStoreState>((set) => ({
  alerts: [],
  addAlert: (newAlert) => set((state) => ({
    // Add new alert to the front, keep only the latest 10
    alerts: [newAlert, ...state.alerts].slice(0, 10)
  })),
  clearAlerts: () => set({ alerts: [] })
}));