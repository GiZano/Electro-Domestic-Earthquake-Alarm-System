import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ServerCrash } from 'lucide-react-native';
import { useAppTheme } from '../theme/useTheme';
import { MONO } from '../theme';

interface Props {
  title?: string;
  message?: string;
}

export function ErrorBanner({
  title = "CONNECTION ERROR",
  message = "Unable to reach the server. Please check your connection and try again."
}: Readonly<Props>) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);

  return (
    <View style={styles.container}>
      <ServerCrash size={44} color={colors.alert} />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const createStyles = (c: ReturnType<typeof useAppTheme>["colors"]) =>
  StyleSheet.create({
    container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
    title: { marginTop: 15, fontSize: 18, fontWeight: 'bold', color: c.text, textAlign: 'center', fontFamily: MONO, letterSpacing: 1 },
    message: { marginTop: 8, fontSize: 14, color: c.textSecondary, textAlign: 'center', lineHeight: 20 }
  });