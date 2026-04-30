import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { AlertTriangle } from 'lucide-react-native';
import { useAlertStore } from '../store/useAlertStore';

export function AlertHistoryList() {
  const { alerts } = useAlertStore();

  if (alerts.length === 0) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Recent Activity</Text>
      <FlatList
        data={alerts}
        keyExtractor={(item, index) => `${item.timestamp}-${index}`}
        scrollEnabled={false} // Disable scroll if placed inside a ScrollView parent
        renderItem={({ item }) => (
          <View style={styles.row}>
            <AlertTriangle size={16} color="#dc2626" />
            <View style={styles.textContainer}>
              <Text style={styles.message}>Zone {item.zone_id} • Mag {item.magnitude.toFixed(1)}</Text>
              <Text style={styles.time}>{new Date(item.timestamp).toLocaleTimeString()}</Text>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 20, paddingTop: 20, borderTopWidth: 1, borderTopColor: '#f3f4f6' },
  title: { fontSize: 14, fontWeight: '700', color: '#374151', marginBottom: 12, textTransform: 'uppercase' },
  row: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fef2f2', padding: 12, borderRadius: 8, marginBottom: 8 },
  textContainer: { marginLeft: 10, flex: 1, flexDirection: 'row', justifyContent: 'space-between' },
  message: { fontSize: 14, fontWeight: '600', color: '#991b1b' },
  time: { fontSize: 12, color: '#dc2626' }
});