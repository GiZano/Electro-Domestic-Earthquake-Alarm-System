import { Radio, ServerCrash } from "lucide-react-native";
import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import MapView, { Callout, Marker, PROVIDER_DEFAULT } from "react-native-maps";
import { useSensors } from "../../api/hooks/useDashboard";
import { useSensorStatistics } from "../../api/hooks/useSensors";

/**
 * Sub-component for the Marker Callout.
 * CRITICAL: By isolating the hook here, we guarantee useSensorStatistics 
 * is ONLY called when the user taps the marker, preventing 200 concurrent requests.
 */
const SensorCalloutDetails = ({ sensor }: { sensor: any }) => {
  const { data: stats, isLoading, isError } = useSensorStatistics(sensor.id);

  return (
    <View style={styles.calloutContainer}>
      <Text style={styles.calloutTitle}>Sensor ID: {sensor.id}</Text>
      
      <View style={styles.statusRow}>
        <Radio
          size={14}
          color={sensor.active ? "#16a34a" : "#dc2626"}
        />
        <Text
          style={[
            styles.statusText,
            { color: sensor.active ? "#16a34a" : "#dc2626" },
          ]}
        >
          {sensor.active ? "Active" : "Offline"}
        </Text>
      </View>

      <View style={styles.statsDivider} />

      {isLoading ? (
        <ActivityIndicator size="small" color="#4f46e5" style={{ marginTop: 5 }} />
      ) : isError ? (
        <Text style={styles.errorText}>Data unavailable</Text>
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
  // Fetch the global list of sensors (shares cache with Dashboard)
  const { data: sensors, isLoading, isError } = useSensors();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#dc2626" />
        <Text style={styles.loadingText}>Connecting to Global Network...</Text>
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.centered}>
        <ServerCrash size={48} color="#dc2626" />
        <Text style={styles.errorTitle}>Map Unavailable</Text>
        <Text style={styles.errorText}>Could not reach the sensor network.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={{
          latitude: 41.9028, // Default fallback (Rome, Italy)
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
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  map: {
    width: "100%",
    height: "100%",
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f9fafb",
  },
  loadingText: {
    marginTop: 15,
    fontSize: 16,
    color: "#4b5563",
    fontWeight: "500",
  },
  errorTitle: {
    marginTop: 15,
    fontSize: 20,
    fontWeight: "bold",
    color: "#1f2937",
  },
  errorText: {
    marginTop: 5,
    fontSize: 14,
    color: "#6b7280",
    textAlign: "center",
  },
  calloutContainer: {
    padding: 10,
    width: 160,
    backgroundColor: "white",
    borderRadius: 8,
  },
  calloutTitle: {
    fontWeight: "800",
    fontSize: 14,
    marginBottom: 6,
    color: "#111827",
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 8,
  },
  statusText: {
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  statsDivider: {
    height: 1,
    backgroundColor: "#e5e7eb",
    marginVertical: 6,
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 4,
  },
  statsLabel: {
    fontSize: 12,
    color: "#4b5563",
    fontWeight: "500",
  },
  statsValue: {
    fontSize: 14,
    fontWeight: "700",
    color: "#4f46e5",
  },
});