import React, {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { Vibration, Platform } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { API_BASE_URL, MOBILE_WS_TOKEN } from "../constants/config";
import { useAlertStore } from '../store/useAlertStore';
import { usePreferencesStore } from '../store/usePrefrencesStore';

// --- NOTIFICATION HANDLER ---
// Tells the app how to handle notifications received while the app is actively open
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
  zone_id: number;
  magnitude: number;
  message: string;
  timestamp: string;
}

interface WebSocketContextType {
  isConnected: boolean;
  lastAlert: AlertMessage | null;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

// --- CONSTANTS ---
const SOS_VIBRATION_PATTERN = [
  0, 200, 100, 200, 100, 200, // 3 short
  300, 500, 300, 500, 300, 500, // 3 long
  300, 200, 100, 200, 100, 200, // 3 short
];

const MAX_RECONNECT_DELAY = 30000; // 30 seconds max backoff

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastAlert, setLastAlert] = useState<AlertMessage | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null); 
  const reconnectAttempts = useRef<number>(0);

  // Startup: Request Notification Permissions
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
    if (ws.current?.readyState === WebSocket.OPEN) return;

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
        const message: AlertMessage = JSON.parse(event.data);
        console.log("⚡ ALERT RECEIVED:", message);

        // ALWAYS update state (Dashboard UI relies on this)
        setLastAlert(message);
        useAlertStore.getState().addAlert(message); 

        // GATE: Check user preferences before disturbing them
        const { notificationsEnabled } = usePreferencesStore.getState();

        if (message.type === "CRITICAL" && notificationsEnabled) {
          // Hardware Haptics
          Vibration.vibrate(SOS_VIBRATION_PATTERN);
          
          // Local OS Push Notification
          Notifications.scheduleNotificationAsync({
            content: {
              title: "⚠️ CRITICAL SEISMIC ALERT",
              body: `Magnitude ${message.magnitude.toFixed(1)} detected. ${message.message}`,
              sound: true,
              priority: Notifications.AndroidNotificationPriority.MAX,
            },
            trigger: null, // Fire immediately
          });
        }
      } catch (err) {
        console.error("❌ Error parsing WS message:", err);
      }
    };

    ws.current.onclose = () => {
      console.log("❌ WS Disconnected");
      setIsConnected(false);

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

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  return (
    <WebSocketContext.Provider value={{ isConnected, lastAlert }}>
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