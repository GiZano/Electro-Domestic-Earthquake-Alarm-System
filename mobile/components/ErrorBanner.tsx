import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ServerCrash } from 'lucide-react-native';

interface Props {
  title?: string;
  message?: string;
}

export function ErrorBanner({ 
  title = "Connection Error", 
  message = "Unable to reach the server. Please check your connection and try again." 
}: Props) {
  return (
    <View style={styles.container}>
      <ServerCrash size={48} color="#dc2626" />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { marginTop: 15, fontSize: 20, fontWeight: 'bold', color: '#1f2937', textAlign: 'center' },
  message: { marginTop: 8, fontSize: 14, color: '#6b7280', textAlign: 'center', lineHeight: 20 }
});