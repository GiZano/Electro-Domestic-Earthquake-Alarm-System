import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { AlertTriangle, Sparkles } from 'lucide-react-native';
import { useAlertStore } from '../store/useAlertStore';

export function AlertHistoryList() {
  const { alerts, reports } = useAlertStore();

  if (alerts.length === 0) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Recent Activity</Text>
      <FlatList
        data={alerts}
        keyExtractor={(item, index) => `${item.timestamp}-${index}`}
        scrollEnabled={false} // Disable scroll if placed inside a ScrollView parent
        renderItem={({ item }) => {
          const report = item.alert_id != null ? reports[item.alert_id] : undefined;
          return (
            <View style={styles.row}>
              <AlertTriangle size={16} color="#dc2626" />
              <View style={styles.textContainer}>
                <Text style={styles.message}>Zone {item.zone_id} • Mag {item.magnitude.toFixed(1)}</Text>
                <Text style={styles.time}>{new Date(item.timestamp).toLocaleTimeString()}</Text>
              </View>
              {report && (
                <View style={styles.reportCard}>
                  {report.status === 'COMPLETED' ? (
                    <>
                      <View style={styles.reportHeader}>
                        <Sparkles size={12} color="#7c3aed" />
                        <Text style={styles.reportTitle}>AI Report</Text>
                      </View>
                      <Text style={styles.reportSummary}>{report.summary}</Text>
                      {report.recommendations && report.recommendations.length > 0 && (
                        <Text style={styles.reportRecommendations}>
                          {report.recommendations.map((r) => `• ${r}`).join('\n')}
                        </Text>
                      )}
                    </>
                  ) : (
                    <Text style={styles.reportUnavailable}>AI Report Unavailable</Text>
                  )}
                </View>
              )}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 20, paddingTop: 20, borderTopWidth: 1, borderTopColor: '#f3f4f6' },
  title: { fontSize: 14, fontWeight: '700', color: '#374151', marginBottom: 12, textTransform: 'uppercase' },
  row: { flexDirection: 'column', backgroundColor: '#fef2f2', padding: 12, borderRadius: 8, marginBottom: 8 },
  textContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  message: { fontSize: 14, fontWeight: '600', color: '#991b1b' },
  time: { fontSize: 12, color: '#dc2626' },
  reportCard: { marginTop: 10, backgroundColor: '#f5f3ff', padding: 10, borderRadius: 8 },
  reportHeader: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
  reportTitle: { fontSize: 11, fontWeight: '700', color: '#7c3aed', textTransform: 'uppercase', letterSpacing: 0.5 },
  reportSummary: { fontSize: 13, color: '#4c1d95', lineHeight: 18 },
  reportRecommendations: { marginTop: 6, fontSize: 12, color: '#6d28d9', lineHeight: 16 },
  reportUnavailable: { fontSize: 12, fontStyle: 'italic', color: '#991b1b' },
});
