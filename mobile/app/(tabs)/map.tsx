import { Radio } from "lucide-react-native";
import React from "react";
import { ActivityIndicator, Platform, StyleSheet, Text, View } from "react-native";
import MapView, { Callout, Marker, PROVIDER_DEFAULT } from "react-native-maps";
import { useSensors } from "../../api/hooks/useDashboard";
import { useSensorStatistics } from "../../api/hooks/useSensors";
import { LoadingSkeleton } from "../../components/LoadingSkeleton";
import { ErrorBanner } from "../../components/ErrorBanner";
import { useAppTheme } from "../../theme/useTheme";
import { MONO } from "../../theme";
import { darkMapStyle, lightMapStyle } from "../../theme/mapStyle";

type ThemeColors = ReturnType<typeof useAppTheme>["colors"];

const CalloutStats = ({ stats, colors }: { stats: any; colors: ThemeColors }) => {
  const styles = createStyles(colors);
  return (
    <View style={styles.statsRow}>
      <Text style={styles.statsLabel}>TOTAL READINGS:</Text>
      <Text style={styles.statsValue}>{stats?.total_readings || 0}</Text>
    </View>
  );
};

const SensorCalloutDetails = ({ sensor, colors }: { sensor: any; colors: ThemeColors }) => {
  const { data: stats, isLoading, isError } = useSensorStatistics(sensor.id);
  const styles = createStyles(colors);

  let content: React.JSX.Element;
  if (isLoading) {
    content = <ActivityIndicator size="small" color={colors.live} style={{ marginTop: 5 }} />;
  } else if (isError) {
    content = <Text style={{ fontSize: 12, color: colors.textMuted, marginTop: 4 }}>DATA UNAVAILABLE</Text>;
  } else {
    content = <CalloutStats stats={stats} colors={colors} />;
  }

  return (
    <View style={styles.calloutContainer}>
      <Text style={styles.calloutTitle}>SENSOR {sensor.id}</Text>

      <View style={styles.statusRow}>
        <Radio size={14} color={sensor.active ? colors.live : colors.alert} />
        <Text style={[styles.statusText, { color: sensor.active ? colors.live : colors.alert }]}>
          {sensor.active ? "ACTIVE" : "OFFLINE"}
        </Text>
      </View>

      <View style={styles.statsDivider} />

      {content}
    </View>
  );
};

export default function MapScreen() {
  const { data: sensors, isLoading, isError } = useSensors();
  const { colors, isDark } = useAppTheme();
  const styles = createStyles(colors);

  if (isLoading) {
    return <LoadingSkeleton message="Connecting to Global Network..." />;
  }

  if (isError) {
    return (
      <ErrorBanner
        title="Map Unavailable"
        message="Could not reach the sensor network. Please check your connection."
      />
    );
  }

  const mapStyle = Platform.OS === "android" ? (isDark ? darkMapStyle : lightMapStyle) : undefined;

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        customMapStyle={mapStyle}
        initialRegion={{
          latitude: 41.9028,
          longitude: 12.4964,
          latitudeDelta: 5,
          longitudeDelta: 5,
        }}
      >
        {sensors?.map((sensor: any) => (
          <Marker
            key={sensor.id}
            coordinate={{ latitude: sensor.latitude, longitude: sensor.longitude }}
            pinColor={sensor.active ? "green" : "red"}
          >
            <Callout tooltip={false}>
              {/* Inject the lazy-loading details component */}
              <SensorCalloutDetails sensor={sensor} colors={colors} />
            </Callout>
          </Marker>
        ))}
      </MapView>
    </View>
  );
}

const createStyles = (c: ThemeColors) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: c.bg },
    map: { width: "100%", height: "100%" },
    calloutContainer: { padding: 10, width: 180, backgroundColor: c.surfaceAlt, borderRadius: 8, borderColor: c.borderStrong, borderWidth: 1 },
    calloutTitle: { fontWeight: "800", fontSize: 14, marginBottom: 6, color: c.text, fontFamily: MONO, letterSpacing: 1 },
    statusRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 8 },
    statusText: { fontSize: 12, fontWeight: "600", textTransform: "uppercase", letterSpacing: 0.5, fontFamily: MONO },
    statsDivider: { height: 1, backgroundColor: c.border, marginVertical: 6 },
    statsRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 4 },
    statsLabel: { fontSize: 11, color: c.textSecondary, fontWeight: "500", fontFamily: MONO },
    statsValue: { fontSize: 14, fontWeight: "700", color: c.live, fontFamily: MONO },
  });
