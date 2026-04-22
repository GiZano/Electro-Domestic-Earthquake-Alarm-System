import { Tabs } from "expo-router";
import { Map, ShieldCheck, Settings } from "lucide-react-native";
import React from "react";
// 💡 IMPORT THE INSETS HOOK
import { useSafeAreaInsets } from "react-native-safe-area-context"; 

export default function TabLayout() {
  // 💡 GET SYSTEM DIMENSIONS
  const insets = useSafeAreaInsets(); 

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#dc2626", // Red color for active state
        tabBarInactiveTintColor: "#6b7280", // Gray color for inactive state
        tabBarStyle: {
          // 💡 DYNAMICALLY ADD SYSTEM INSETS TO OUR BASE VALUES
          paddingBottom: 5 + insets.bottom, 
          height: 60 + insets.bottom,       
          borderTopWidth: 1,
          borderTopColor: "#e5e7eb",
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "600",
          marginBottom: 5,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Monitor",
          tabBarIcon: ({ color }) => <ShieldCheck size={28} color={color} />,
        }}
      />

      <Tabs.Screen
        name="map"
        options={{
          title: "Sensors",
          tabBarIcon: ({ color }) => <Map size={28} color={color} />,
        }}
      />

      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ color }) => <Settings size={28} color={color} />,
        }}
      />
    </Tabs>
  );
}