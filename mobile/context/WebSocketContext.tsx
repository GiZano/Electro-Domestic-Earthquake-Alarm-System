import React, {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useCallback,
} from "react";
import { Vibration, Platform } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { API_BASE_URL, MOBILE_WS_TOKEN } from "../constants/config";
import { useAlertStore } from '../store/useAlertStore';
import { usePreferencesStore } from '../store/usePreferencesStore';

// --- NOTIFICATION HANDLER ---
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: usePreferencesStore.getState().notificationsEnabled,
    shouldPlaySound: usePreferencesStore.getState().notificationsEnabled,
    shouldSetBadge: false,
  }),
});

// --- TYPES & INTERFACES ---
export interface AlertMessage {
  type: string;
  alert_id?: number;
  zone_id: number;
  magnitude: number;
  message: string;
  timestamp: string;
}

export interface EmergencyReportMessage {
  type: "EMERGENCY_REPORT";
  alert_id: number;
  report_id: number;
  zone_id: number;
  magnitude: number;
  status: "COMPLETED" | "FAILED";
  summary?: string;
  recommendations?: string[];
  timestamp: string;
}

interface WebSocketContextType {
  isConnected: boolean;
  lastAlert: AlertMessage | null;
  lastReport: EmergencyReportMessage | null;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

// --- CONSTANTS ---
const SOS_VIBRATION_PATTERN = [
  0, 200, 100, 200, 100, 200, 
  300, 500, 300, 500, 300, 500, 
  300, 200, 100, 200, 100, 200, 
];

const MAX_RECONNECT_DELAY = 30000;

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastAlert, setLastAlert] = useState<AlertMessage | null>(null);
  const [lastReport, setLastReport] = useState<EmergencyReportMessage | null>(null);
  
  // Bring in the offline mode flag
  const isOfflineMode = usePreferencesStore((state) => state.isOfflineMode);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null); 
  const reconnectAttempts = useRef<number>(0);
  
  // Track intentional closures so the onclose handler doesn't aggressively reconnect
  const intentionalClose = useRef<boolean>(false);

  useEffect(() => {
    const registerForPushNotificationsAsync = async () => {
      if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
          name: 'default',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#FF231F7C',
        });
      }
      if (Device.isDevice) {
        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }
        if (finalStatus !== 'granted') {
          console.warn('Failed to get push token for push notification!');
          return;
        }
      }
    };
    registerForPushNotificationsAsync();
  }, []);
  
  const connect = useCallback(() => {
    if (usePreferencesStore.getState().isOfflineMode) return;
    
    // FIX: Dobbiamo bloccare anche se il socket è in stato "CONNECTING" (0), 
    // altrimenti React ne crea due quasi contemporaneamente.
    if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    intentionalClose.current = false;
    const wsUrl = `${API_BASE_URL.replace("http", "ws")}/ws/alerts?token=${MOBILE_WS_TOKEN}`;
    console.log(`🔌 Attempting WS Connection: ${wsUrl}`);

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log("✅ WS Connected Successfully");
      setIsConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.current.onmessage = (event: WebSocketMessageEvent) => {
      try {
        const message: any = JSON.parse(event.data);
        const { notificationsEnabled } = usePreferencesStore.getState();

        // 🤖 AI Emergency Report (generated asynchronously by the local Ollama worker)
        if (message.type === "EMERGENCY_REPORT") {
          const report: EmergencyReportMessage = message;
          console.log("🤖 AI REPORT RECEIVED:", report);
          setLastReport(report);
          useAlertStore.getState().addReport(report);

          if (notificationsEnabled) {
            Notifications.scheduleNotificationAsync({
              content: {
                title: report.status === "COMPLETED" ? "🤖 AI Emergency Report" : "🤖 AI Report non disponibile",
                body:
                  report.status === "COMPLETED"
                    ? report.summary ?? "Emergency report generated."
                    : "The AI report could not be generated. Contact local authorities.",
                sound: true,
                priority: Notifications.AndroidNotificationPriority.MAX,
              },
              trigger: null,
            });
          }
          return;
        }

        const alert: AlertMessage = message;
        console.log("⚡ ALERT RECEIVED:", alert);

        setLastAlert(alert);
        useAlertStore.getState().addAlert(alert);

        if (alert.type === "CRITICAL" && notificationsEnabled) {
          Vibration.vibrate(SOS_VIBRATION_PATTERN);
          Notifications.scheduleNotificationAsync({
            content: {
              title: "⚠️ CRITICAL SEISMIC ALERT",
              body: `Magnitude ${alert.magnitude.toFixed(1)} detected. ${alert.message}`,
              sound: true,
              priority: Notifications.AndroidNotificationPriority.MAX,
            },
            trigger: null,
          });
        }
      } catch (err) {
        console.error("❌ Error parsing WS message:", err);
      }
    };

    ws.current.onclose = () => {
      console.log("❌ WS Disconnected");
      setIsConnected(false);

      // Do not attempt to reconnect if the user intentionally went offline
      if (intentionalClose.current) return;

      const delay = Math.min(
        1000 * Math.pow(2, reconnectAttempts.current),
        MAX_RECONNECT_DELAY
      );
      
      console.log(`⏳ Reconnecting in ${delay / 1000} seconds...`);
      reconnectTimeout.current = setTimeout(() => {
        reconnectAttempts.current += 1;
        connect();
      }, delay);
    };

    ws.current.onerror = (error: Event) => {
      console.error("⚠️ WS Error:", error);
    };
  }, []);

  // 💡 THE NEW WATCHER: React to the offline toggle changing
  useEffect(() => {
    if (isOfflineMode) {
      console.log("🛑 Offline Mode Activated. Shutting down WS...");
      intentionalClose.current = true;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.close();
        ws.current = null; // Pulizia profonda
      }
    } else {
      console.log("🟢 Online Mode Activated. Booting up WS...");
      connect();
    }

    // Cleanup function per quando l'app viene chiusa
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, [isOfflineMode, connect]);
  
  // 💡 IL SECONDO useEffect(() => { connect() }) È STATO ELIMINATO COMPLETAMENTE!

  return (
    <WebSocketContext.Provider
      value={useMemo(
        () => ({ isConnected, lastAlert, lastReport }),
        [isConnected, lastAlert, lastReport]
      )}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return context;
};