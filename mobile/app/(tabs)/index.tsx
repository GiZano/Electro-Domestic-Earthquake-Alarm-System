import { ShieldAlert, ShieldCheck, Wifi, WifiOff, Activity } from "lucide-react-native";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { StyleSheet, Text, View, ScrollView, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";
import { VictoryChart, VictoryLine, VictoryAxis, VictoryLabel } from "victory-native";
import { useWebSocket } from "../../context/WebSocketContext";
import { useSensors, useZones, useZoneReadings } from "../../api/hooks/useDashboard";
import { LoadingSkeleton } from "../../components/LoadingSkeleton";
import { ErrorBanner } from "../../components/ErrorBanner";
import { AlertHistoryList } from "../../components/AlertHistoryList";
import { useAppTheme } from "../../theme/useTheme";
import { createQuakeGuardTheme } from "../../theme/victory";
import { MONO } from "../../theme";
import { estimateMagnitude, thresholdOf } from "../../utils/magnitude";

const WINDOW_MAX = 60; // samples kept in the sliding window
const WINDOW_SECONDS = 30; // time domain of the seismograph
const RIGHT_PAD = 8; // breathing room right of x=0 so live samples stay in-field

type ThemeColors = ReturnType<typeof useAppTheme>["colors"];

function TopBar({ isConnected, colors }: Readonly<{ isConnected: boolean; colors: ThemeColors }>) {
  const styles = createStyles(colors);
  return (
    <View style={styles.topBar}>
      <Text style={styles.headerTitle}>NETWORK STATUS</Text>
      <View style={styles.connectionBadge}>
        {isConnected ? <Wifi size={16} color={colors.live} /> : <WifiOff size={16} color={colors.alert} />}
        <View style={[styles.statusDot, { backgroundColor: isConnected ? colors.live : colors.alert }]} />
        <Text style={[styles.connectionText, { color: isConnected ? colors.live : colors.alert }]}>
          {isConnected ? "LIVE" : "OFFLINE"}
        </Text>
      </View>
    </View>
  );
}

function HeroSection({ isAlertActive, animatedStyle, colors }: Readonly<{
  isAlertActive: boolean;
  animatedStyle: any;
  colors: ThemeColors;
}>) {
  const styles = createStyles(colors);
  return (
    <View style={styles.heroSection}>
      <Animated.View style={[styles.iconContainer, animatedStyle]}>
        {isAlertActive ? (
          <ShieldAlert size={90} color={colors.alert} />
        ) : (
          <ShieldCheck size={90} color={colors.live} />
        )}
      </Animated.View>
      <Text style={[styles.statusText, { color: isAlertActive ? colors.alert : colors.live }]}>
        {isAlertActive ? "⚠ SEISMIC ALERT ⚠" : "SYSTEM SECURE"}
      </Text>
    </View>
  );
}

function AlertBanner({ lastAlert, colors }: Readonly<{ lastAlert: any; colors: ThemeColors }>) {
  const styles = createStyles(colors);
  return (
    <View style={styles.alertDetails}>
      <Text style={styles.alertValue}>MAG {lastAlert.magnitude.toFixed(1)}</Text>
      <Text style={styles.alertMessage}>{`"${lastAlert.message}"`}</Text>
    </View>
  );
}

function AiReportCard({ lastReport, colors }: Readonly<{ lastReport: any; colors: ThemeColors }>) {
  const styles = createStyles(colors);
  if (!lastReport) return null;

  if (lastReport.status === "FAILED") {
    return (
      <View style={styles.reportCardFailed}>
        <Text style={styles.reportCardTitle}>AI REPORT // UNAVAILABLE</Text>
        <Text style={styles.reportCardBody}>The AI report could not be generated. Verify with local authorities.</Text>
      </View>
    );
  }

  return (
    <View style={styles.reportCard}>
      <Text style={styles.reportCardTitle}>AI EMERGENCY REPORT</Text>
      <Text style={styles.reportCardBody}>{lastReport.summary}</Text>
      {lastReport.recommendations && lastReport.recommendations.length > 0 && (
        <View style={styles.reportRecommendations}>
          {[...new Set<string>(lastReport.recommendations)].map((r) => (
            <Text key={r} style={styles.reportRecommendationItem}>{`> ${r}`}</Text>
          ))}
        </View>
      )}
    </View>
  );
}

/** Horizontal strip of PostGIS zones — one seismograph per zone. */
function ZoneSelector({ zones, selectedId, onSelect, colors }: Readonly<{
  zones: any[];
  selectedId: number | undefined;
  onSelect: (id: number) => void;
  colors: ThemeColors;
}>) {
  const styles = createStyles(colors);
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.zoneStrip}
    >
      {zones.map((zone) => {
        const active = zone.id === selectedId;
        return (
          <Pressable
            key={zone.id}
            onPress={() => onSelect(zone.id)}
            style={[styles.zoneChip, active && styles.zoneChipActive]}
          >
            <Text style={[styles.zoneChipText, active && styles.zoneChipTextActive]}>
              {zone.city.toUpperCase()}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

/** Per-zone telemetry strip: nodes, current magnitude, signal state. */
function ZoneSummaryStrip({ activeNodes, totalNodes, latestMagnitude, isAlertActive, colors }: Readonly<{
  activeNodes: number;
  totalNodes: number;
  latestMagnitude: number | null;
  isAlertActive: boolean;
  colors: ThemeColors;
}>) {
  const styles = createStyles(colors);
  const mag = latestMagnitude ?? 0;
  const magColor = mag >= 4.5 ? colors.alert : mag >= 4.0 ? colors.caution : colors.live;

  return (
    <View style={styles.summaryRow}>
      <View style={styles.summaryItem}>
        <Text style={styles.summaryLabel}>NODES</Text>
        <Text style={styles.summaryValue}>{activeNodes} / {totalNodes}</Text>
      </View>
      <View style={styles.summaryItem}>
        <Text style={styles.summaryLabel}>MAG</Text>
        <Text style={[styles.summaryValue, { color: magColor }]}>{mag.toFixed(2)}</Text>
      </View>
      <View style={styles.summaryItem}>
        <Text style={styles.summaryLabel}>SIGNAL</Text>
        <View style={styles.signalRow}>
          <Activity size={16} color={isAlertActive ? colors.alert : colors.live} />
          <Text style={[styles.summaryValueSmall, { color: isAlertActive ? colors.alert : colors.live }]}>
            {isAlertActive ? "ALERT" : "STABLE"}
          </Text>
        </View>
      </View>
    </View>
  );
}

type WindowPoint = { x: number; y: number; t: number }; // x = seconds relative to newest
type WindowEntry = { t: number; y: number }; // t = epoch ms (merge key)

function NetworkChart({ points, isAlertActive, colors }: Readonly<{
  points: WindowPoint[];
  isAlertActive: boolean;
  colors: ThemeColors;
}>) {
  const styles = createStyles(colors);
  const theme = useMemo(() => createQuakeGuardTheme(colors), [colors]);
  const last = points[points.length - 1];
  const lineColor = last
    ? thresholdOf(last.y) === "alert"
      ? colors.alert
      : thresholdOf(last.y) === "caution"
        ? colors.caution
        : colors.live
    : colors.live;

  if (points.length === 0) {
    return (
      <Text style={styles.chartEmpty}>AWAITING TELEMETRY // ZONE ...</Text>
    );
  }

  // Right breathing room so the newest live sample (x≈0) never touches or
  // spills past the plot edge — that read as "the graph starts out of field".
  const magTicks = [3.5, 4.0, 4.5]; // MIN / MED / ALTO thresholds on a linear MAG axis

  // Plot in magnitude units (linear scale) instead of raw sensor values
  // (log-compressed near the noise floor — that made the 3.0/3.5 ticks crowd).
  const data = points.map(({ x, y, t }) => ({ x, y: estimateMagnitude(y), t }));

  const CHART_WIDTH = 450; // victory-native default
  const PAD_LEFT = 52;
  const PAD_RIGHT = 12;
  const PAD_BOTTOM = 46;
  const chartHeight = isAlertActive ? 150 : 200;

  // TIME under the X axis, centered on the middle of the DATA domain (-15s,
  // i.e. between the 20s and 10s ticks) rather than the physical chart center,
  // which sits right-of-center because of the RIGHT_PAD breathing room.
  const spanX = WINDOW_SECONDS + RIGHT_PAD;
  const timeX = PAD_LEFT + ((WINDOW_SECONDS - 15) / spanX) * (CHART_WIDTH - PAD_LEFT - PAD_RIGHT);
  const timeY = chartHeight - PAD_BOTTOM + 34;

  return (
    <VictoryChart
      theme={theme}
      height={chartHeight}
      padding={{ top: 8, bottom: PAD_BOTTOM, left: PAD_LEFT, right: PAD_RIGHT }}
      domain={{ x: [-WINDOW_SECONDS, RIGHT_PAD], y: [3.0, 5.0] }}
    >
      <VictoryLabel
        text="TIME"
        x={timeX}
        y={timeY}
        textAnchor="middle"
        style={{ fill: colors.tick, fontFamily: MONO, fontSize: 10 }}
      />
      <VictoryAxis
        dependentAxis
        orientation="left"
        offsetX={PAD_LEFT}
        tickValues={magTicks}
        tickFormat={(t) => `${t.toFixed(1)}`}
        label="MAG"
        style={{
          axisLabel: { padding: 38, fill: colors.tick, fontFamily: MONO, fontSize: 10 },
        }}
      />
      <VictoryAxis
        orientation="bottom"
        tickValues={[-30, -20, -10, 0]}
        tickFormat={(t) => `${Math.abs(Math.round(t))}s`}
      />
      <VictoryLine
        style={{
          data: { stroke: lineColor, strokeWidth: 2 },
        }}
        data={data}
        x="x"
        y="y"
        interpolation="linear"
      />
    </VictoryChart>
  );
}

export default function MonitorScreen() {
  const { isConnected, lastAlert, lastReport } = useWebSocket();
  const { colors } = useAppTheme();
  const [isAlertActive, setIsAlertActive] = useState(false);
  const [selectedZoneId, setSelectedZoneId] = useState<number | undefined>(undefined);
  const [window, setWindow] = useState<WindowPoint[]>([]);
  const pulse = useSharedValue(1);
  const alertTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const styles = createStyles(colors);

  const { data: sensors, isLoading: loadingSensors, isError: errorSensors } = useSensors();
  const { data: zones, isLoading: loadingZones, isError: errorZones } = useZones();
  const { data: readings, isLoading: loadingReadings, isError: errorReadings } = useZoneReadings(selectedZoneId, WINDOW_MAX);

  const totalSensors = sensors?.length || 0;
  const activeSensors = sensors?.filter((s: any) => s.active).length || 0;
  const selectedZone = zones?.find((z: any) => z.id === selectedZoneId);

  // Default to the first zone once the PostGIS list is available.
  useEffect(() => {
    if (selectedZoneId === undefined && zones && zones.length > 0) {
      setSelectedZoneId(zones[0].id);
    }
  }, [zones, selectedZoneId]);

  // Reset the sliding window when switching zone.
  useEffect(() => {
    setWindow([]);
  }, [selectedZoneId]);

  // Merge incoming readings into the sliding window (push newest, drop oldest).
  // The time axis is anchored to the wall clock (Date.now), NOT to the newest
  // sample: stale readings drift to the left and leave the window, while live
  // ones enter at the right edge. Anchoring to the newest sample instead pins
  // a finished run at the right edge forever ("lines going out of the field").
  useEffect(() => {
    if (!readings || readings.length === 0) return;
    setWindow((prev) => {
      const now = Date.now();
      const merged = new Map<number, WindowEntry>();
      for (const p of prev) merged.set(p.t, { t: p.t, y: p.y });
      for (const r of readings) {
        const t = Date.parse(r.recorded_at);
        if (Number.isNaN(t)) continue;
        merged.set(t, { t, y: r.value });
      }
      const list = [...merged.values()].filter(({ t }) => (now - t) / 1000 <= WINDOW_SECONDS);
      if (list.length === 0) return prev;
      return list
        .sort((a, b) => a.t - b.t)
        .slice(-WINDOW_MAX)
        .map(({ t, y }) => ({
          // Clamp to the domain so nothing can ever spill past the plot edges.
          x: Math.max(-WINDOW_SECONDS, Math.min(RIGHT_PAD, (t - now) / 1000)),
          y,
          t,
        }));
    });
  }, [readings, selectedZoneId]);

  const latestMagnitude = useMemo(() => {
    if (!readings || readings.length === 0) return null;
    return estimateMagnitude(readings[0].value);
  }, [readings]);

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

  const loading = loadingSensors || loadingZones || loadingReadings;
  const errored = errorSensors || errorZones || errorReadings;

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: colors.bg }]} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <TopBar isConnected={isConnected} colors={colors} />

        <HeroSection isAlertActive={isAlertActive} animatedStyle={animatedStyle} colors={colors} />

        {isAlertActive && lastAlert && <AlertBanner lastAlert={lastAlert} colors={colors} />}

        <AiReportCard lastReport={lastReport} colors={colors} />

        <View style={styles.dashboardCard}>
          {errored ? (
            <ErrorBanner />
          ) : loading ? (
            <LoadingSkeleton message="Establishing telemetry link..." />
          ) : (
            <>
              <ZoneSelector
                zones={zones || []}
                selectedId={selectedZoneId}
                onSelect={setSelectedZoneId}
                colors={colors}
              />

              <View style={styles.chartHeader}>
                <Text style={styles.chartTitle} numberOfLines={1}>
                  SEISMOGRAPH // {selectedZone?.city?.toUpperCase() ?? "ZONE"}
                </Text>
                <Text style={styles.chartSubtitle}>Z-ACCEL // RAW</Text>
              </View>

              <ZoneSummaryStrip
                activeNodes={activeSensors}
                totalNodes={totalSensors}
                latestMagnitude={latestMagnitude}
                isAlertActive={isAlertActive}
                colors={colors}
              />

              <View style={styles.chartContainer}>
                <NetworkChart points={window} isAlertActive={isAlertActive} colors={colors} />
              </View>
            </>
          )}
        </View>

        <AlertHistoryList />
      </ScrollView>
    </SafeAreaView>
  );
}

const createStyles = (c: ThemeColors) =>
  StyleSheet.create({
    safeArea: { flex: 1 },
    scrollContent: { flexGrow: 1, padding: 20 },
    topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
    headerTitle: { fontSize: 18, fontWeight: "700", color: c.text, letterSpacing: 1.5, fontFamily: MONO },
    connectionBadge: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      backgroundColor: c.surface,
      borderColor: c.border,
      borderWidth: 1,
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: 20,
    },
    statusDot: { width: 8, height: 8, borderRadius: 4 },
    connectionText: { fontSize: 12, fontWeight: "800", fontFamily: MONO },
    heroSection: { alignItems: 'center', marginVertical: 10 },
    iconContainer: { marginBottom: 10 },
    statusText: { fontSize: 24, fontWeight: "900", textAlign: "center", letterSpacing: 2, fontFamily: MONO },
    dashboardCard: {
      backgroundColor: c.surface,
      borderColor: c.border,
      borderWidth: 1,
      borderRadius: 16,
      padding: 20,
      marginTop: 10,
    },
    zoneStrip: { gap: 8, paddingVertical: 4, marginBottom: 16 },
    zoneChip: {
      paddingHorizontal: 14,
      paddingVertical: 8,
      borderRadius: 20,
      backgroundColor: c.surfaceAlt,
      borderColor: c.border,
      borderWidth: 1,
    },
    zoneChipActive: {
      borderColor: c.live,
      backgroundColor: c.bg,
    },
    zoneChipText: { fontSize: 11, fontWeight: "700", color: c.textSecondary, letterSpacing: 1, fontFamily: MONO },
    zoneChipTextActive: { color: c.live },
    chartHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10, gap: 8 },
    chartTitle: { fontSize: 13, fontWeight: "700", color: c.text, letterSpacing: 1.2, fontFamily: MONO, flexShrink: 1 },
    chartSubtitle: { fontSize: 10, color: c.textMuted, letterSpacing: 1, fontFamily: MONO, flexShrink: 0 },
    summaryRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      borderTopWidth: 1,
      borderTopColor: c.border,
      borderBottomWidth: 1,
      borderBottomColor: c.border,
      paddingVertical: 10,
      marginBottom: 10,
    },
    summaryItem: { alignItems: 'flex-start', flex: 1 },
    summaryLabel: { fontSize: 10, color: c.textMuted, fontWeight: "700", letterSpacing: 1.2, fontFamily: MONO },
    summaryValue: { fontSize: 16, fontWeight: "700", color: c.text, fontFamily: MONO, marginTop: 2 },
    summaryValueSmall: { fontSize: 14, fontWeight: "700", fontFamily: MONO },
    signalRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
    chartContainer: { marginVertical: 4 },
    chartEmpty: { textAlign: 'center', color: c.textMuted, fontFamily: MONO, fontSize: 12, paddingVertical: 60, letterSpacing: 1 },
    alertDetails: { marginBottom: 10, padding: 12, backgroundColor: c.bg, borderColor: c.alert, borderWidth: 1, borderRadius: 12, alignItems: 'center' },
    alertValue: { fontSize: 18, fontWeight: "800", color: c.alert, fontFamily: MONO },
    alertMessage: { fontSize: 14, fontStyle: "italic", color: c.textSecondary },
    reportCard: { marginBottom: 10, padding: 12, backgroundColor: c.surfaceAlt, borderColor: c.border, borderWidth: 1, borderRadius: 12 },
    reportCardFailed: { marginBottom: 10, padding: 12, backgroundColor: c.surfaceAlt, borderColor: c.caution, borderWidth: 1, borderRadius: 12 },
    reportCardTitle: { fontSize: 12, fontWeight: "800", color: c.info, marginBottom: 6, letterSpacing: 1.2, fontFamily: MONO },
    reportCardBody: { fontSize: 13, color: c.textSecondary, lineHeight: 18 },
    reportRecommendations: { marginTop: 8 },
    reportRecommendationItem: { fontSize: 12, color: c.text, lineHeight: 16, fontFamily: MONO },
  });