import { ShieldAlert, ShieldCheck, Wifi, WifiOff } from "lucide-react-native";
import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";
import { useWebSocket } from "../../context/WebSocketContext";

/**
 * MonitorScreen Component.
 * Displays the real-time status of the seismic system.
 * Uses local timers to manage alert duration, independent of device system time.
 */
export default function MonitorScreen() {
  const { isConnected, lastAlert } = useWebSocket();

  // Local state to manage the visual alert status
  const [isAlertActive, setIsAlertActive] = useState(false);

  // Animation shared value
  const pulse = useSharedValue(1);

  // Timer reference to handle cleanup and debounce
  const alertTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Effect: Handle incoming alerts.
   * Triggered whenever `lastAlert` changes via WebSocket.
   * Sets local state to active and starts a 60-second countdown.
   */
  useEffect(() => {
    if (lastAlert) {
      console.log("[Monitor] New alert received. Activating UI.");
      setIsAlertActive(true);

      // Clear existing timer if a new alert arrives (extend duration)
      if (alertTimerRef.current) {
        clearTimeout(alertTimerRef.current);
      }

      // Set a local timer to dismiss the alert after 60 seconds
      alertTimerRef.current = setTimeout(() => {
        console.log("[Monitor] Alert timeout reached. Resetting UI.");
        setIsAlertActive(false);
      }, 60000);
    }

    // Cleanup on unmount
    return () => {
      if (alertTimerRef.current) {
        clearTimeout(alertTimerRef.current);
      }
    };
  }, [lastAlert]);

  /**
   * Effect: Handle Pulse Animation.
   * synchronized with `isAlertActive` state.
   */
  useEffect(() => {
    if (isAlertActive) {
      pulse.value = withRepeat(
        withSequence(
          withTiming(1.2, { duration: 300, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: 300, easing: Easing.inOut(Easing.ease) }),
        ),
        -1, // Infinite loop
        true, // Reverse
      );
    } else {
      // Reset animation smoothly
      pulse.value = withTiming(1, { duration: 300 });
    }
  }, [isAlertActive]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
    opacity: isAlertActive ? pulse.value : 1,
  }));

  // Helper to determine background color
  const backgroundColor = isAlertActive ? "#fef2f2" : "#f0fdf4";
  const textColor = isAlertActive ? "#991b1b" : "#166534";

  return (
    <SafeAreaView style={[styles.container, { backgroundColor }]} edges={['top']}>
      {/* Connection Status Indicator */}
      <View style={styles.connectionBadge}>
        {isConnected ? (
          <Wifi size={20} color="#16a34a" />
        ) : (
          <WifiOff size={20} color="#dc2626" />
        )}
        <Text
          style={[
            styles.connectionText,
            { color: isConnected ? "#16a34a" : "#dc2626" },
          ]}
        >
          {isConnected ? "LIVE" : "OFFLINE"}
        </Text>
      </View>

      {/* Main Visual Indicator */}
      <Animated.View style={[styles.iconContainer, animatedStyle]}>
        {isAlertActive ? (
          <ShieldAlert size={120} color="#dc2626" />
        ) : (
          <ShieldCheck size={120} color="#16a34a" />
        )}
      </Animated.View>

      {/* Status Text */}
      <Text style={[styles.statusText, { color: textColor }]}>
        {isAlertActive ? "⚠️ SEISMIC ALERT ⚠️" : "SYSTEM SECURE"}
      </Text>

      {/* Alert Details or Idle Message */}
      {isAlertActive && lastAlert ? (
        <View style={styles.alertDetails}>
          <View style={styles.alertRow}>
            <Text style={styles.alertLabel}>ZONE:</Text>
            <Text style={styles.alertValue}>{lastAlert.zone_id}</Text>
          </View>
          <View style={styles.alertRow}>
            <Text style={styles.alertLabel}>MAGNITUDE:</Text>
            <Text style={styles.alertValue}>
              {lastAlert.magnitude.toFixed(1)}
            </Text>
          </View>
          <Text style={styles.alertMessage}>"{lastAlert.message}"</Text>
        </View>
      ) : (
        <Text style={styles.subText}>
          Network active. Monitoring sensors...
        </Text>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  connectionBadge: {
    position: "absolute",
    top: 20, // Adjusted for SafeArea dynamically
    right: 20,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "rgba(255,255,255,0.8)",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  connectionText: {
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  iconContainer: {
    marginBottom: 40,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 5,
  },
  statusText: {
    fontSize: 28,
    fontWeight: "900",
    marginBottom: 10,
    textAlign: "center",
    letterSpacing: 1,
  },
  subText: {
    fontSize: 16,
    color: "#6b7280",
    textAlign: "center",
    marginTop: 10,
  },
  alertDetails: {
    marginTop: 30,
    width: "100%",
    padding: 20,
    backgroundColor: "#fee2e2",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#fecaca",
  },
  alertRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(0,0,0,0.05)",
    paddingBottom: 4,
  },
  alertLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#7f1d1d",
  },
  alertValue: {
    fontSize: 18,
    fontWeight: "800",
    color: "#b91c1c",
  },
  alertMessage: {
    fontSize: 16,
    fontStyle: "italic",
    marginTop: 10,
    textAlign: "center",
    color: "#991b1b",
  },
});