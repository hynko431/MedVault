import { Tabs } from "expo-router";
import { Image } from "react-native";
export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#2563EB",
        tabBarInactiveTintColor: "#9CA3AF",
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopWidth: 0.5,
          borderTopColor: "#E5E7EB",
        },
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: "Home",
          tabBarIcon: ({ size }) => (
            <Image
              source={require("../assets/icons/home.png")}
              style={{
                width: size,
                height: size,
              }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="upload"
        options={{
          title: "Upload",
          tabBarIcon: ({ size }) => (
            <Image
              source={require("../assets/icons/upload.png")}
              style={{
                width: size,
                height: size,
              }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: "Search",
          tabBarIcon: ({ size }) => (
            <Image
              source={require("../assets/icons/search1.png")}
              style={{
                width: size,
                height: size,
              }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="family"
        options={{
          title: "Family",
          tabBarIcon: ({ size }) => (
            <Image
              source={require("../assets/icons/family.png")}
              style={{
                width: size,
                height: size,
              }}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="reminders"
        options={{
          title: "Reminders",
          tabBarIcon: ({ size }) => (
            <Image
              source={require("../assets/icons/reminder.png")}
              style={{
                width: size,
                height: size,
              }}
            />
          ),
        }}
      />
    </Tabs>
  );
}
