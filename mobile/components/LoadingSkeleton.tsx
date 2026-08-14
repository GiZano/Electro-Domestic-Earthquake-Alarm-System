import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { useAppTheme } from '../theme/useTheme';
import { MONO } from '../theme';

interface Props {
  message?: string;
}

export function LoadingSkeleton({ message = "LOADING DATA..." }: Readonly<Props>) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={colors.alert} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const createStyles = (c: ReturnType<typeof useAppTheme>["colors"]) =>
  StyleSheet.create({
    container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
    text: { marginTop: 15, fontSize: 14, color: c.textSecondary, fontWeight: '500', textAlign: 'center', fontFamily: MONO, letterSpacing: 1 }
  });