import React, {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { Vibration } from "react-native";
// 💡 IMPORT MOBILE_WS_TOKEN HERE
import { API_BASE_URL, MOBILE_WS_TOKEN } from "../constants/config";

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
  
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    // 💡 USE THE IMPORTED TOKEN HERE
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

        setLastAlert(message);

        if (message.type === "CRITICAL") {
          Vibration.vibrate(SOS_VIBRATION_PATTERN);
        }
      } catch (err) {
        console.error("❌ Error parsing WS message:", err);
      }
    };

    ws.current.onclose = () => {
      console.log("❌ WS Disconnected");
      setIsConnected(false);
      scheduleReconnection();
    };

    ws.current.onerror = (error: Event) => {
      console.error("⚠️ WS Error:", error);
    };
  }, []);

  const scheduleReconnection = useCallback(() => {
    const delay = Math.min(
      1000 * Math.pow(2, reconnectAttempts.current),
      MAX_RECONNECT_DELAY
    );
    
    console.log(`⏳ Reconnecting in ${delay / 1000} seconds...`);
    reconnectTimeout.current = setTimeout(() => {
      reconnectAttempts.current += 1;
      connect();
    }, delay);
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
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