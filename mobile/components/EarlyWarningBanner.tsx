import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { Clock } from "lucide-react-native";
import { useAppTheme } from "../theme/useTheme";
import { MONO } from "../theme";
import { AlertMessage } from "../context/WebSocketContext";

// S-wave velocity ~3.5 km/s, but P-wave is ~6.0 km/s.
// We warn for the destructive S-wave:
const V_S = 3.5;

function haversine(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371; // km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * 
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export function EarlyWarningBanner({ 
  alert, 
  userLocation 
}: { 
  alert: AlertMessage;
  userLocation: { latitude: number; longitude: number } | null;
}) {
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  
  const [etaSeconds, setEtaSeconds] = useState<number | null>(null);

  useEffect(() => {
    if (!alert.latitude || !alert.longitude || !alert.origin_time || !userLocation) return;
    
    const distanceKm = haversine(
      userLocation.latitude, 
      userLocation.longitude, 
      alert.latitude, 
      alert.longitude
    );
    
    // Time for destructive S-waves to arrive
    const travelTimeS = distanceKm / V_S;
    const originMs = Date.parse(alert.origin_time);
    
    const updateCountdown = () => {
      const nowMs = Date.now();
      const arrivalMs = originMs + (travelTimeS * 1000);
      const remainingS = Math.max(0, Math.floor((arrivalMs - nowMs) / 1000));
      setEtaSeconds(remainingS);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [alert, userLocation]);

  if (etaSeconds === null) return null;

  const isImpacted = etaSeconds === 0;

  return (
    <View style={[styles.container, isImpacted ? styles.containerImpact : {}]}>
      <View style={styles.header}>
        <Clock size={16} color={isImpacted ? colors.bg : colors.live} />
        <Text style={[styles.title, isImpacted ? styles.textImpact : {}]}>
          EARLY WARNING ETA
        </Text>
      </View>
      <Text style={[styles.etaValue, isImpacted ? styles.textImpact : {}]}>
        {isImpacted ? "BRACE FOR IMPACT" : `T-${etaSeconds}s`}
      </Text>
      <Text style={[styles.subtitle, isImpacted ? styles.textImpact : {}]}>
        {isImpacted ? "SHAKING IMMINENT" : "DESTRUCTIVE S-WAVE APPROACHING"}
      </Text>
    </View>
  );
}

const createStyles = (c: any) =>
  StyleSheet.create({
    container: {
      marginBottom: 10,
      padding: 12,
      backgroundColor: c.surfaceAlt,
      borderColor: c.live,
      borderWidth: 1,
      borderRadius: 12,
      alignItems: "center",
    },
    containerImpact: {
      backgroundColor: c.alert,
      borderColor: c.alert,
    },
    header: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      marginBottom: 4,
    },
    title: {
      fontSize: 12,
      fontWeight: "800",
      color: c.live,
      fontFamily: MONO,
      letterSpacing: 1.2,
    },
    etaValue: {
      fontSize: 32,
      fontWeight: "900",
      color: c.live,
      fontFamily: MONO,
    },
    subtitle: {
      fontSize: 11,
      color: c.textSecondary,
      fontFamily: MONO,
      marginTop: 2,
    },
    textImpact: {
      color: c.bg,
    }
  });
