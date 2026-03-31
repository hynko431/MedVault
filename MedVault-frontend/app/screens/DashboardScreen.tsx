import AsyncStorage from "@react-native-async-storage/async-storage";
import { router } from "expo-router";
import { useState } from "react";
import {
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

interface FamilyMember {
  id: string;
  name: string;
  relation: string;
}

export default function DashboardScreen() {
  const [selectedMember, setSelectedMember] = useState("1");

  const familyMembers: FamilyMember[] = [
    { id: "1", name: "John Doe", relation: "Self" },
    { id: "2", name: "Jane Doe", relation: "Spouse" },
  ];

  const handleLogout = async () => {
    await AsyncStorage.removeItem("isLoggedIn");
    router.replace("/auth/AuthOptionsScreen");
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <Text style={styles.title}>Good Morning 👋</Text>

        <Text style={styles.sectionTitle}>Family Members</Text>
        <FlatList
          horizontal
          data={familyMembers}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => setSelectedMember(item.id)}
              style={[
                styles.memberCard,
                selectedMember === item.id && styles.memberSelected,
              ]}
            >
              <Text style={styles.memberName}>{item.name}</Text>
              <Text style={styles.memberRelation}>{item.relation}</Text>
            </Pressable>
          )}
        />

        {/* LOGOUT */}
        <Pressable onPress={handleLogout} style={styles.logoutBtn}>
          <Text style={styles.logoutText}>Logout</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB",
    padding: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 12,
  },
  memberCard: {
    backgroundColor: "#FFF",
    padding: 16,
    borderRadius: 12,
    marginRight: 12,
  },
  memberSelected: {
    borderWidth: 2,
    borderColor: "#2563EB",
  },
  memberName: {
    fontWeight: "600",
  },
  memberRelation: {
    fontSize: 12,
    color: "#6B7280",
  },
  logoutBtn: {
    marginTop: 40,
    alignSelf: "center",
  },
  logoutText: {
    color: "red",
    fontWeight: "600",
    fontSize: 16,
  },
});
