import React from "react";
// 💡 IMPORT Alert and TouchableOpacity
import { View, Text, StyleSheet, Switch, Alert, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
// 💡 ADD Trash2 icon
import { Settings as SettingsIcon, Bell, WifiOff, Trash2 } from "lucide-react-native";
import { usePreferencesStore } from "../../store/usePrefrencesStore";
// 💡 IMPORT the store
import { useAlertStore } from "../../store/useAlertStore";

export default function SettingsScreen() {
  const { isOfflineMode, notificationsEnabled, setOfflineMode, toggleNotifications } = usePreferencesStore();
  // 💡 Consume the orphaned action and the alerts array (to disable the button if empty)
  const { clearAlerts, alerts } = useAlertStore();

  const handleClearHistory = () => {
    if (alerts.length === 0) return;
    
    Alert.alert(
      "Clear History",
      "Are you sure you want to delete all recent alerts?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Clear", 
          style: "destructive", 
          onPress: () => {
            clearAlerts();
            console.log("[Settings] Alert history cleared.");
          } 
        }
      ]
    );
  };

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

          {/* 💡 Removed styles.lastRow from here */}
          <View style={styles.settingRow}>
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

          {/* 💡 NEW ROW: Clear History */}
          <TouchableOpacity 
            style={[styles.settingRow, styles.lastRow]} 
            onPress={handleClearHistory}
            disabled={alerts.length === 0}
          >
            <View style={styles.settingLabelContainer}>
              <Trash2 size={24} color={alerts.length === 0 ? "#d1d5db" : "#dc2626"} />
              <Text style={[styles.settingLabel, { color: alerts.length === 0 ? "#9ca3af" : "#374151" }]}>
                Clear Alert History
              </Text>
            </View>
          </TouchableOpacity>

        </View>
      </View>
    </SafeAreaView>
  );
}

// ... [styles remain exactly the same]
const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f9fafb" },
  container: { flex: 1, padding: 20 },
  header: { flexDirection: "row", alignItems: "center", marginBottom: 30, marginTop: 10, gap: 10 },
  headerTitle: { fontSize: 28, fontWeight: "bold", color: "#1f2937" },
  card: { backgroundColor: "white", borderRadius: 16, padding: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  settingRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: "#f3f4f6" },
  lastRow: { borderBottomWidth: 0 },
  settingLabelContainer: { flexDirection: "row", alignItems: "center", gap: 12 },
  settingLabel: { fontSize: 16, fontWeight: "500", color: "#374151" },
});