import { Radio, ServerCrash } from "lucide-react-native";
import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import MapView, { Callout, Marker, PROVIDER_DEFAULT } from "react-native-maps";
import { useSensors } from "../../api/hooks/useDashboard";
import { useSensorStatistics } from "../../api/hooks/useSensors";
import { LoadingSkeleton } from "../../components/LoadingSkeleton";
import { ErrorBanner } from "../../components/ErrorBanner";

const SensorCalloutDetails = ({ sensor }: { sensor: any }) => {
  const { data: stats, isLoading, isError } = useSensorStatistics(sensor.id);

  return (
    <View style={styles.calloutContainer}>
      <Text style={styles.calloutTitle}>Sensor ID: {sensor.id}</Text>
      
      <View style={styles.statusRow}>
        <Radio size={14} color={sensor.active ? "#16a34a" : "#dc2626"} />
        <Text style={[styles.statusText, { color: sensor.active ? "#16a34a" : "#dc2626" }]}>
          {sensor.active ? "Active" : "Offline"}
        </Text>
      </View>

      <View style={styles.statsDivider} />

      {isLoading ? (
        <ActivityIndicator size="small" color="#4f46e5" style={{ marginTop: 5 }} />
      ) : isError ? (
        <Text style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>Data unavailable</Text>
      ) : (
        <View style={styles.statsRow}>
          <Text style={styles.statsLabel}>Total Readings:</Text>
          <Text style={styles.statsValue}>{stats?.total_readings || 0}</Text>
        </View>
      )}
    </View>
  );
};

export default function MapScreen() {
  const { data: sensors, isLoading, isError } = useSensors();

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

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
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
              <SensorCalloutDetails sensor={sensor} />
            </Callout>
          </Marker>
        ))}
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  map: { width: "100%", height: "100%" },
  calloutContainer: { padding: 10, width: 160, backgroundColor: "white", borderRadius: 8 },
  calloutTitle: { fontWeight: "800", fontSize: 14, marginBottom: 6, color: "#111827" },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 8 },
  statusText: { fontSize: 12, fontWeight: "600", textTransform: "uppercase", letterSpacing: 0.5 },
  statsDivider: { height: 1, backgroundColor: "#e5e7eb", marginVertical: 6 },
  statsRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 4 },
  statsLabel: { fontSize: 12, color: "#4b5563", fontWeight: "500" },
  statsValue: { fontSize: 14, fontWeight: "700", color: "#4f46e5" },
});