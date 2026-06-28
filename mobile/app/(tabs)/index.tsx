import { ShieldAlert, ShieldCheck, Wifi, WifiOff, Activity } from "lucide-react-native";
import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";
import { VictoryChart, VictoryLine, VictoryTheme } from "victory-native";
import { useWebSocket } from "../../context/WebSocketContext";
import { useSensors, useRecentReadings } from "../../api/hooks/useDashboard";
import { LoadingSkeleton } from "../../components/LoadingSkeleton";
import { ErrorBanner } from "../../components/ErrorBanner";
import { AlertHistoryList } from "../../components/AlertHistoryList";

export default function MonitorScreen() {
  const { isConnected, lastAlert } = useWebSocket();
  const [isAlertActive, setIsAlertActive] = useState(false);
  const pulse = useSharedValue(1);
  const alertTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: sensors, isLoading: loadingSensors, isError: errorSensors } = useSensors();
  const { data: readings, isLoading: loadingReadings, isError: errorReadings } = useRecentReadings();

  const totalSensors = sensors?.length || 0;
  const activeSensors = sensors?.filter((s: any) => s.active).length || 0;

  useEffect(() => {
    if (lastAlert) {
      setIsAlertActive(true);
      if (alertTimerRef.current) clearTimeout(alertTimerRef.current);
      alertTimerRef.current = setTimeout(() => {
        setIsAlertActive(false);
      }, 60000);
    }
    return () => {
      if (alertTimerRef.current) clearTimeout(alertTimerRef.current);
    };
  }, [lastAlert]);

  useEffect(() => {
    if (isAlertActive) {
      pulse.value = withRepeat(
        withSequence(
          withTiming(1.2, { duration: 300, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: 300, easing: Easing.inOut(Easing.ease) }),
        ),
        -1,
        true,
      );
    } else {
      pulse.value = withTiming(1, { duration: 300 });
    }
  }, [isAlertActive, pulse]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
    opacity: isAlertActive ? pulse.value : 1,
  }));

  const backgroundColor = isAlertActive ? "#fef2f2" : "#f9fafb";
  const textColor = isAlertActive ? "#991b1b" : "#1f2937";

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor }]} edges={['top']}>
      <ScrollView 
        contentContainerStyle={styles.scrollContent} 
        showsVerticalScrollIndicator={false}
      >
        {/* Top Bar */}
        <View style={styles.topBar}>
          <Text style={styles.headerTitle}>Network Status</Text>
          <View style={styles.connectionBadge}>
            {isConnected ? <Wifi size={16} color="#16a34a" /> : <WifiOff size={16} color="#dc2626" />}
            <Text style={[styles.connectionText, { color: isConnected ? "#16a34a" : "#dc2626" }]}>
              {isConnected ? "LIVE" : "OFFLINE"}
            </Text>
          </View>
        </View>

        {/* Hero Section */}
        <View style={styles.heroSection}>
          <Animated.View style={[styles.iconContainer, animatedStyle]}>
            {isAlertActive ? (
              <ShieldAlert size={100} color="#dc2626" />
            ) : (
              <ShieldCheck size={100} color="#16a34a" />
            )}
          </Animated.View>
          <Text style={[styles.statusText, { color: textColor }]}>
            {isAlertActive ? "⚠️ SEISMIC ALERT ⚠️" : "SYSTEM SECURE"}
          </Text>
        </View>

        {/* Alert Banner */}
        {isAlertActive && lastAlert && (
          <View style={styles.alertDetails}>
            <Text style={styles.alertValue}>Mag: {lastAlert.magnitude.toFixed(1)}</Text>
            <Text style={styles.alertMessage}>{`"${lastAlert.message}"`}</Text>
          </View>
        )}

        {/* Dashboard Card */}
        <View style={styles.dashboardCard}>
          {errorSensors || errorReadings ? (
            <ErrorBanner />
          ) : loadingSensors || loadingReadings ? (
            <LoadingSkeleton />
          ) : (
            <>
              <View style={styles.summaryRow}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Active Nodes</Text>
                  <Text style={styles.summaryValue}>{activeSensors} / {totalSensors}</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Signal Status</Text>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <Activity size={18} color="#16a34a" />
                    <Text style={[styles.summaryValue, { color: "#16a34a" }]}>Stable</Text>
                  </View>
                </View>
              </View>

              <View style={styles.chartContainer}>
                <Text style={styles.chartTitle}>Live Network Seismograph</Text>
                {readings && readings.length > 0 ? (
                  <VictoryChart 
                    theme={VictoryTheme.material} 
                    height={isAlertActive ? 150 : 220} // Adattamento dinamico
                    padding={{ top: 10, bottom: 30, left: 40, right: 10 }}
                  >
                    <VictoryLine
                      style={{
                        data: { stroke: isAlertActive ? "#dc2626" : "#4f46e5", strokeWidth: 2 }
                      }}
                      data={readings}
                      x="device_timestamp"
                      y="value"
                    />
                  </VictoryChart>
                ) : (
                  <Text style={{ textAlign: 'center', color: "#6b7280" }}>Awaiting telemetry...</Text>
                )}
              </View>
              
              <AlertHistoryList />
            </>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  scrollContent: { flexGrow: 1, padding: 20 },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  headerTitle: { fontSize: 24, fontWeight: "bold", color: "#111827" },
  connectionBadge: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#ffffff", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  connectionText: { fontSize: 12, fontWeight: "800" },
  heroSection: { alignItems: 'center', marginVertical: 10 },
  iconContainer: { marginBottom: 10 },
  statusText: { fontSize: 26, fontWeight: "900", textAlign: "center" },
  dashboardCard: { 
    backgroundColor: "white", 
    borderRadius: 20, 
    padding: 20, 
    elevation: 3, 
    marginTop: 10 
  },
  summaryRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    borderBottomWidth: 1, 
    borderBottomColor: "#f3f4f6", 
    paddingBottom: 15, 
    marginBottom: 10,
    flexShrink: 0 
  },
  summaryItem: { alignItems: 'flex-start' },
  summaryLabel: { fontSize: 12, color: "#6b7280", fontWeight: "600", textTransform: "uppercase" },
  summaryValue: { fontSize: 20, fontWeight: "bold", color: "#1f2937" },
  chartContainer: { marginVertical: 10 },
  chartTitle: { fontSize: 16, fontWeight: "700", color: "#374151" },
  alertDetails: { marginBottom: 10, padding: 10, backgroundColor: "#fee2e2", borderRadius: 12, alignItems: 'center' },
  alertValue: { fontSize: 18, fontWeight: "800", color: "#b91c1c" },
  alertMessage: { fontSize: 14, fontStyle: "italic", color: "#991b1b" }
});