import { create } from 'zustand';
import { AlertMessage, EmergencyReportMessage } from '../context/WebSocketContext';

interface AlertStoreState {
  alerts: AlertMessage[];
  reports: Record<number, EmergencyReportMessage>;
  addAlert: (alert: AlertMessage) => void;
  addReport: (report: EmergencyReportMessage) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertStoreState>((set) => ({
  alerts: [],
  reports: {},
  addAlert: (newAlert) => set((state) => ({
    // Add new alert to the front, keep only the latest 10
    alerts: [newAlert, ...state.alerts].slice(0, 10)
  })),
  addReport: (newReport) => set((state) => ({
    reports: { ...state.reports, [newReport.alert_id]: newReport }
  })),
  clearAlerts: () => set({ alerts: [], reports: {} })
}));
