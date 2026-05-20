import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';

interface Props {
  message?: string;
}

export function LoadingSkeleton({ message = "Loading data..." }: Props) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#dc2626" />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  text: { marginTop: 15, fontSize: 16, color: '#4b5563', fontWeight: '500', textAlign: 'center' }
});