import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { AlertTriangle, Sparkles } from 'lucide-react-native';
import { useAlertStore } from '../store/useAlertStore';
import { useZones } from '../api/hooks/useDashboard';
import { useAppTheme } from '../theme/useTheme';
import { MONO } from '../theme';

export function AlertHistoryList() {
  const { alerts, reports } = useAlertStore();
  const { data: zones } = useZones();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);

  const zoneName = (zoneId: number): string => {
    const city = (zones ?? []).find((z: any) => z.id === zoneId)?.city;
    return city ? city.toUpperCase() : `ZONE ${zoneId}`;
  };

  if (alerts.length === 0) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>RECENT ACTIVITY</Text>
      <FlatList
        data={alerts}
        keyExtractor={(item, index) => `${item.timestamp}-${index}`}
        scrollEnabled={false} // Disable scroll if placed inside a ScrollView parent
        renderItem={({ item }) => {
          const report = item.alert_id != null ? reports[item.alert_id] : undefined;
          return (
            <View style={styles.row}>
              <AlertTriangle size={16} color={colors.alert} />
              <View style={styles.textContainer}>
                <Text style={styles.message}>{zoneName(item.zone_id)} // MAG {item.magnitude.toFixed(1)}</Text>
                <Text style={styles.time}>{new Date(item.timestamp).toLocaleTimeString()}</Text>
              </View>
              {report && (
                <View style={styles.reportCard}>
                  {report.status === 'COMPLETED' ? (
                    <>
                      <View style={styles.reportHeader}>
                        <Sparkles size={12} color={colors.info} />
                        <Text style={styles.reportTitle}>AI REPORT</Text>
                      </View>
                      <Text style={styles.reportSummary}>{report.summary}</Text>
                      {report.recommendations && report.recommendations.length > 0 && (
                        <Text style={styles.reportRecommendations}>
                          {report.recommendations.map((r) => `> ${r}`).join('\n')}
                        </Text>
                      )}
                    </>
                  ) : (
                    <Text style={styles.reportUnavailable}>AI REPORT UNAVAILABLE</Text>
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

const createStyles = (c: ReturnType<typeof useAppTheme>["colors"]) =>
  StyleSheet.create({
    container: { marginTop: 20, paddingTop: 20, borderTopWidth: 1, borderTopColor: c.border },
    title: { fontSize: 12, fontWeight: '700', color: c.textSecondary, marginBottom: 12, letterSpacing: 1.2, fontFamily: MONO },
    row: { flexDirection: 'column', backgroundColor: c.surface, borderColor: c.border, borderWidth: 1, padding: 12, borderRadius: 10, marginBottom: 8 },
    textContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    message: { fontSize: 13, fontWeight: '600', color: c.text, fontFamily: MONO },
    time: { fontSize: 11, color: c.textMuted, fontFamily: MONO },
    reportCard: { marginTop: 10, backgroundColor: c.surfaceAlt, borderColor: c.border, borderWidth: 1, padding: 10, borderRadius: 8 },
    reportHeader: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
    reportTitle: { fontSize: 10, fontWeight: '700', color: c.info, textTransform: 'uppercase', letterSpacing: 1, fontFamily: MONO },
    reportSummary: { fontSize: 12, color: c.textSecondary, lineHeight: 18 },
    reportRecommendations: { marginTop: 6, fontSize: 11, color: c.text, lineHeight: 16, fontFamily: MONO },
    reportUnavailable: { fontSize: 11, fontStyle: 'italic', color: c.caution, fontFamily: MONO },
  });