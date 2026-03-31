import AsyncStorage from "@react-native-async-storage/async-storage";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";

import { apiRequest } from "../../src/api/api";
import { getFamily } from "../../src/api/family";

export default function Dashboard() {
  console.log("🔥 DASHBOARD ACTIVE");
  console.log("DASHBOARD LOADED");
  const [family, setFamily] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    testBackend();   // backend test
    init();
  }, []);

  // ✅ Correct backend test route
  const testBackend = async () => {
    try {
      const data = await apiRequest("/api/test");
      console.log("Backend says:", data);
    } catch (err: any) {
      console.log("Backend error:", err.message);
    }
  };

  const init = async () => {
    const token = await AsyncStorage.getItem("token");

    // 🔥 TEMPORARY: comment redirect for testing
    // if (!token) {
    //   router.replace("/auth/AuthOptionsScreen");
    //   return;
    // }

    try {
      const data = await getFamily();
      setFamily(data);
    } catch (err: any) {
      console.log("Family API error:", err.message);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await AsyncStorage.multiRemove(["token", "isLoggedIn"]);
    router.replace("/auth/AuthOptionsScreen");
  };

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
        <Text>Loading dashboard...</Text>
      </View>
    );
  }

  return (
    <View style={{ padding: 20 }}>
      <Text style={{ fontSize: 22, marginBottom: 10 }}>Dashboard</Text>

      {family.length === 0 && <Text>No family members yet</Text>}

      {family.map((f) => (
        <Text key={f.id}>
          {f.name} ({f.relation})
        </Text>
      ))}

      <Pressable onPress={logout} style={{ marginTop: 30 }}>
        <Text style={{ color: "red", fontWeight: "600" }}>Logout</Text>
      </Pressable>
    </View>
  );
}