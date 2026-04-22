import React from "react";
import { View, Text, StyleSheet, Switch } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Settings as SettingsIcon, Bell, WifiOff } from "lucide-react-native";
import { usePreferencesStore } from "../../store/usePrefrencesStore";

export default function SettingsScreen() {
  // Pulling our global state directly from Zustand!
  const { isOfflineMode, notificationsEnabled, setOfflineMode, toggleNotifications } = usePreferencesStore();

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.container}>
        <View style={styles.header}>
          <SettingsIcon size={32} color="#dc2626" />
          <Text style={styles.headerTitle}>Settings</Text>
        </View>

        <View style={styles.card}>
          <View style={styles.settingRow}>
            <View style={styles.settingLabelContainer}>
              <Bell size={24} color="#4b5563" />
              <Text style={styles.settingLabel}>Enable Notifications</Text>
            </View>
            <Switch
              value={notificationsEnabled}
              onValueChange={toggleNotifications}
              trackColor={{ false: "#d1d5db", true: "#fca5a5" }}
              thumbColor={notificationsEnabled ? "#dc2626" : "#9ca3af"}
            />
          </View>

          <View style={[styles.settingRow, styles.lastRow]}>
            <View style={styles.settingLabelContainer}>
              <WifiOff size={24} color="#4b5563" />
              <Text style={styles.settingLabel}>Force Offline Mode</Text>
            </View>
            <Switch
              value={isOfflineMode}
              onValueChange={setOfflineMode}
              trackColor={{ false: "#d1d5db", true: "#fca5a5" }}
              thumbColor={isOfflineMode ? "#dc2626" : "#9ca3af"}
            />
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f9fafb",
  },
  container: {
    flex: 1,
    padding: 20,
    // paddingTop: 60 REMOVED! SafeAreaView handles this dynamically now.
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 30,
    marginTop: 10, // Just a little breathing room from the dynamic notch
    gap: 10,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#1f2937",
  },
  card: {
    backgroundColor: "white",
    borderRadius: 16,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  settingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  lastRow: {
    borderBottomWidth: 0,
  },
  settingLabelContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: "500",
    color: "#374151",
  },
});